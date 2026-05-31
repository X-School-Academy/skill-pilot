import { useState, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import {
  AppShell, Header, Navbar, NavLink, Divider, Select, Group,
  MediaQuery, Burger, ScrollArea, useMantineTheme,
} from '@mantine/core';
import axios from 'axios';
import { apiUrl } from '../libs/api-base';
import { resolveSelectedProvider, setSelectedProvider } from '../libs/llm';
import { MAIN_NAV_ITEMS, type MainNavItem } from '../libs/main-nav';

interface LlmProvider { id: string; name: string; }

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

  const isActive = (item: MainNavItem): boolean => {
    if (item.view && currentView) return currentView === item.view;
    if (item.href === '/terminal-histories' && pathname === '/terminal-history') return true;
    if (item.href.includes('?')) return false;
    return pathname === item.href;
  };

  const handleNavClick = (event: React.MouseEvent, item: MainNavItem) => {
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
            {MAIN_NAV_ITEMS.map((item, idx) => {
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
