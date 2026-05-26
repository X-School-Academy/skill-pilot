import { useState, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import {
  AppShell, Header, Navbar, NavLink, Divider, Select, Group,
  MediaQuery, Burger, ScrollArea, useMantineTheme,
} from '@mantine/core';
import {
  IconTerminal2, IconPlus, IconSparkles, IconSchool, IconBriefcase, IconSearch,
  IconChecklist, IconCode, IconHammer, IconRocket, IconProgress, IconWand,
  IconServer, IconCalendar, IconPuzzle, IconUser, IconShieldLock,
  IconBrandDiscord, IconVectorBezier2, IconVideo, IconCamera, IconFolderOpen,
  IconHistory, IconSend,
} from '@tabler/icons-react';
import axios from 'axios';
import { apiUrl } from '../libs/api-base';
import { resolveSelectedProvider, setSelectedProvider } from '../libs/llm';

interface LlmProvider { id: string; name: string; }

interface NavItemDef {
  label: string;
  icon: React.ReactNode;
  href: string;
  view?: string;           // matches /?view=xxx for active detection
  dividerBefore?: string;  // '' = plain divider, 'Label' = labelled divider
}

const NAV_ITEMS: NavItemDef[] = [
  { label: 'Explore',          href: '/?view=explore',                              view: 'explore',      icon: <IconSparkles size="1rem" /> },
  { dividerBefore: '', label: 'New Session', href: '/?view=home',                   view: 'home',         icon: <IconPlus size="1rem" /> },
  { label: 'Live Sessions',    href: '/terminals',                                  icon: <IconTerminal2 size="1rem" /> },
  { label: 'Session Histories', href: '/terminal-histories',                        icon: <IconHistory size="1rem" /> },
  { dividerBefore: 'Workspace', label: 'Learning', href: '/courses',                icon: <IconSchool size="1rem" /> },
  { label: 'Vibe Coding',      href: '/vibe-coding',                               icon: <IconBriefcase size="1rem" /> },
  { label: 'Research',         href: '/research',                                  icon: <IconSearch size="1rem" /> },
  { label: 'Social Media',     href: '/social-media',                              icon: <IconSend size="1rem" /> },
  { label: 'Tasks',            href: '/tasks',                                    icon: <IconChecklist size="1rem" /> },
  { label: 'File Manager',    href: '/file-manager',                             icon: <IconFolderOpen size="1rem" /> },
  { dividerBefore: 'Skill Pilot', label: 'Development', href: '/skill-pilot-development', icon: <IconCode size="1rem" /> },
  { label: 'Codeware',         href: '/codeware',                                  icon: <IconHammer size="1rem" /> },
  { dividerBefore: 'Commercial Project', label: 'Dev Swarm', href: '/dev-swarm',    icon: <IconRocket size="1rem" /> },
  { dividerBefore: '', label: 'Processes',     href: '/?view=processes',    view: 'processes',    icon: <IconProgress size="1rem" /> },
  { label: 'Discord Bot',      href: '/?view=discord-bot',  view: 'discord-bot',  icon: <IconBrandDiscord size="1rem" /> },
  { label: 'Live Avatar',      href: '/live-avatar',                               icon: <IconVideo size="1rem" /> },
  { label: 'Security Cameras', href: '/cameras',                                   icon: <IconCamera size="1rem" /> },
  { dividerBefore: '', label: 'Skills',    href: '/?view=skills',      view: 'skills',      icon: <IconWand size="1rem" /> },
  { label: 'Workflows',        href: '/workflows',                                 icon: <IconVectorBezier2 size="1rem" /> },
  { label: 'MCP Servers',      href: '/?view=mcp-servers',  view: 'mcp-servers',  icon: <IconServer size="1rem" /> },
  { label: 'Schedules',        href: '/?view=schedule',     view: 'schedule',     icon: <IconCalendar size="1rem" /> },
  { label: 'Extensions',       href: '/?view=extensions',   view: 'extensions',   icon: <IconPuzzle size="1rem" /> },
  { label: 'AI & Security',    href: '/?view=ai-security',  view: 'ai-security',  icon: <IconShieldLock size="1rem" /> },
  { label: 'Profile',          href: '/?view=profile',      view: 'profile',      icon: <IconUser size="1rem" /> },
];

interface MainLayoutProps {
  children: React.ReactNode;
  title?: string;
}

export default function MainLayout({ children, title }: MainLayoutProps) {
  const router = useRouter();
  const theme = useMantineTheme();
  const isDevMode = process.env.NODE_ENV === 'development';
  const [opened, setOpened] = useState(false);
  const [llmProviders, setLlmProviders] = useState<LlmProvider[]>([]);
  const [llmProvider, setLlmProvider] = useState<string | null>(null);

  useEffect(() => {
    axios.get(apiUrl('/api/llm/providers'))
      .then((res) => {
        const providers: LlmProvider[] = res.data.providers || [];
        const serverDefault: string = res.data.default || '';
        setLlmProviders(providers);
        const defaultId = resolveSelectedProvider(providers, serverDefault, 'gemini');
        if (defaultId) setSelectedProvider(defaultId);
        setLlmProvider(defaultId);
      })
      .catch(() => {});
  }, []);

  const { pathname, query } = router;
  const currentView = pathname === '/' && typeof query.view === 'string' ? query.view : null;

  const isActive = (item: NavItemDef): boolean => {
    if (item.view) return currentView === item.view;
    if (item.href === '/terminal-histories' && pathname === '/terminal-history') return true;
    if (item.href.includes('?')) return false;
    return pathname === item.href;
  };

  const handleNavClick = (event: React.MouseEvent, item: NavItemDef) => {
    if (event.shiftKey) {
      window.open(item.href, '_blank', 'noopener,noreferrer');
      setOpened(false);
      return;
    }
    void router.push(item.href);
    setOpened(false);
  };

  return (
    <AppShell
      padding={0}
      styles={{
        main: {
          background: theme.colorScheme === 'dark' ? theme.colors.dark[8] : theme.colors.gray[0],
        },
      }}
      navbarOffsetBreakpoint="sm"
      navbar={
        <Navbar p="xs" hiddenBreakpoint="sm" hidden={!opened} width={{ sm: 240 }}>
          <Navbar.Section grow component={ScrollArea}>
            {NAV_ITEMS.map((item, idx) => {
              const elements: React.ReactNode[] = [];
              if (item.dividerBefore !== undefined) {
                elements.push(
                  <Divider
                    key={`d-${idx}`}
                    my="xs"
                    label={item.dividerBefore || undefined}
                    labelPosition="center"
                  />
                );
              }
              elements.push(
                <NavLink
                  key={item.label}
                  label={item.label}
                  icon={item.icon}
                  active={isActive(item)}
                  onClick={(event) => handleNavClick(event, item)}
                />
              );
              return elements;
            })}
          </Navbar.Section>
        </Navbar>
      }
      header={
        <Header
          height={{ base: 60 }}
          p="md"
          styles={{
            root: isDevMode ? { borderBottom: '2px solid #228be6' } : undefined,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', height: '100%', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <MediaQuery largerThan="sm" styles={{ display: 'none' }}>
                <Burger
                  opened={opened}
                  onClick={() => setOpened((o) => !o)}
                  size="sm"
                  color={theme.colors.gray[6]}
                  mr="xl"
                />
              </MediaQuery>
              <a href="/" style={{ display: 'flex', alignItems: 'center' }}>
                <img className="h-10" src="/images/skill-pilot-2.png" alt="Skill Pilot" />
              </a>
            </div>

            <Group spacing="xs">
              {llmProviders.length > 0 && (
                <Select
                  placeholder="LLM"
                  value={llmProvider}
                  onChange={(value) => {
                    if (!value) return;
                    setLlmProvider(value);
                    setSelectedProvider(value);
                  }}
                  data={llmProviders.map((p) => ({ value: p.id, label: p.name }))}
                  size="xs"
                  style={{ width: 200 }}
                />
              )}
            </Group>
          </div>
        </Header>
      }
    >
      {title && (
        <Head>
          <title>{`${title} — Skill Pilot`}</title>
        </Head>
      )}
      <div style={{ height: 'calc(100vh - 60px)', overflowY: 'auto', overflowX: 'hidden' }}>
        {children}
      </div>
    </AppShell>
  );
}
