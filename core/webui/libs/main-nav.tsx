import React from 'react';
import {
  IconTerminal2,
  IconSparkles,
  IconSchool,
  IconBriefcase,
  IconSearch,
  IconChecklist,
  IconCode,
  IconHammer,
  IconRocket,
  IconProgress,
  IconWand,
  IconServer,
  IconCalendar,
  IconPuzzle,
  IconUser,
  IconShieldLock,
  IconBrandDiscord,
  IconVectorBezier2,
  IconVideo,
  IconCamera,
  IconFolderOpen,
  IconHistory,
  IconRobot,
  IconFileText,
  IconMessages,
} from '@tabler/icons-react';

export interface MainNavItem {
  label: string;
  icon: React.ReactNode;
  href: string;
  view?: string;
  dividerBefore?: string;
}

export const MAIN_NAV_ITEMS: MainNavItem[] = [
  { label: 'Explore', href: '/', view: 'explore', icon: <IconSparkles size="1rem" /> },
  { dividerBefore: 'Agent', label: 'Agent Sessions', href: '/agent-sessions', icon: <IconMessages size="1rem" /> },
  { label: 'Session History', href: '/terminal-histories', icon: <IconHistory size="1rem" /> },
  { dividerBefore: 'Workspace', label: 'Learning', href: '/courses', icon: <IconSchool size="1rem" /> },
  { label: 'Vibe Coding', href: '/vibe-coding', icon: <IconBriefcase size="1rem" /> },
  { label: 'Research', href: '/research', icon: <IconSearch size="1rem" /> },
  { label: 'Tasks', href: '/tasks', icon: <IconChecklist size="1rem" /> },
  { label: 'Media', href: '/media', icon: <IconVideo size="1rem" /> },
  { label: 'Documents', href: '/documents', icon: <IconFileText size="1rem" /> },
  { label: 'File Manager', href: '/file-manager', icon: <IconFolderOpen size="1rem" /> },
  { dividerBefore: 'Skill Pilot', label: 'Development', href: '/skill-pilot-development', icon: <IconCode size="1rem" /> },
  { label: 'Codeware', href: '/codeware', icon: <IconHammer size="1rem" /> },
  { dividerBefore: 'Commercial Project', label: 'Dev Swarm', href: '/dev-swarm', icon: <IconRocket size="1rem" /> },
  { dividerBefore: '', label: 'Processes', href: '/processes', view: 'processes', icon: <IconProgress size="1rem" /> },
  { label: 'Live Sessions', href: '/terminals', icon: <IconTerminal2 size="1rem" /> },
  { label: 'Discord Bot', href: '/discord-bot', view: 'discord-bot', icon: <IconBrandDiscord size="1rem" /> },
  { label: 'Live Avatar', href: '/live-avatar', icon: <IconVideo size="1rem" /> },
  { label: 'Security Cameras', href: '/cameras', icon: <IconCamera size="1rem" /> },
  { dividerBefore: '', label: 'Skills', href: '/skills', view: 'skills', icon: <IconWand size="1rem" /> },
  { label: 'Subagents', href: '/subagents', view: 'subagents', icon: <IconRobot size="1rem" /> },
  { label: 'Workflows', href: '/workflows', icon: <IconVectorBezier2 size="1rem" /> },
  { label: 'MCP Servers', href: '/mcp-servers', view: 'mcp-servers', icon: <IconServer size="1rem" /> },
  { label: 'Schedules', href: '/schedules', view: 'schedule', icon: <IconCalendar size="1rem" /> },
  { label: 'Extensions', href: '/extensions', view: 'extensions', icon: <IconPuzzle size="1rem" /> },
  { label: 'AI & Security', href: '/ai-security', view: 'ai-security', icon: <IconShieldLock size="1rem" /> },
  { label: 'Profile', href: '/profile', view: 'profile', icon: <IconUser size="1rem" /> },
];
