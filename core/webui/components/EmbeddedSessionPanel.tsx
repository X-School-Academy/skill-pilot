import React from 'react';
import { ActionIcon, Button, Select, Text, Textarea } from '@mantine/core';
import { IconX } from '@tabler/icons-react';
import { useSessionRoots } from '../libs/session-roots';

type NextNodeTrigger = 'auto_continue' | 'start_by_prompt';

export interface WorkflowExecuteStatus {
  status: string;
  error?: string;
  next_node_trigger?: NextNodeTrigger;
  waiting_for_continue?: boolean;
}

interface EmbeddedSessionPanelProps {
  currentLabel: string;
  liveSessionName: string | null;
  sessionPromptText: string;
  setSessionPromptText: (value: string) => void;
  newSessionWorkflow: string | null;
  newSessionSandbox: boolean;
  setNewSessionSandbox: (value: boolean) => void;
  newSessionAuto: boolean;
  setNewSessionAuto: (value: boolean) => void;
  newSessionNetwork: boolean;
  setNewSessionNetwork: (value: boolean) => void;
  newSessionNextNodeTrigger: NextNodeTrigger;
  setNewSessionNextNodeTrigger: (value: NextNodeTrigger) => void;
  newSessionWorkflowResumeAvailable: boolean;
  newSessionWorkflowResume: boolean;
  setNewSessionWorkflowResume: (value: boolean) => void;
  startingSession: boolean;
  onStart: (path?: string) => void;
  onClose: () => void;
  workflowExecuteStatus: WorkflowExecuteStatus | null;
  workflowSessionActive: boolean;
  continuingWorkflow: boolean;
  onContinueWorkflow: () => void;
  hideSessionRootSelect?: boolean;
}

export default function EmbeddedSessionPanel({
  currentLabel,
  liveSessionName,
  sessionPromptText,
  setSessionPromptText,
  newSessionWorkflow,
  newSessionSandbox,
  setNewSessionSandbox,
  newSessionAuto,
  setNewSessionAuto,
  newSessionNetwork,
  setNewSessionNetwork,
  newSessionNextNodeTrigger,
  setNewSessionNextNodeTrigger,
  newSessionWorkflowResumeAvailable,
  newSessionWorkflowResume,
  setNewSessionWorkflowResume,
  startingSession,
  onStart,
  onClose,
  workflowExecuteStatus,
  workflowSessionActive,
  continuingWorkflow,
  onContinueWorkflow,
  hideSessionRootSelect = false,
}: EmbeddedSessionPanelProps) {
  const {
    sessionRootOptions,
    hasSessionWorktrees,
    selectedSessionPath,
    setSelectedSessionPath,
  } = useSessionRoots();

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: 0,
        border: '1px solid #cfdaf6',
        background: '#ffffff',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 14px',
          borderBottom: '1px solid #cfdaf6',
          background: '#f7f9ff',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <Text size="sm" weight={700}>
            {liveSessionName ? 'Session Terminal' : 'New Session'}
          </Text>
          <Text size="xs" color="dimmed" truncate>
            {liveSessionName ? liveSessionName : currentLabel}
          </Text>
        </div>
        <ActionIcon variant="subtle" onClick={onClose} aria-label="Close session panel">
          <IconX size="1rem" />
        </ActionIcon>
      </div>

      {liveSessionName ? (
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          {workflowExecuteStatus && (workflowExecuteStatus.status === 'error' || workflowExecuteStatus.status === 'terminated') && (
            <div style={{ padding: '8px 12px', borderBottom: '1px solid #cfdaf6', background: '#fde8e8', color: '#c0392b', fontSize: 13 }}>
              Workflow execution failed{workflowExecuteStatus.error ? `: ${workflowExecuteStatus.error}` : ''}
            </div>
          )}
          {workflowExecuteStatus && workflowExecuteStatus.status === 'finished' && (
            <div style={{ padding: '8px 12px', borderBottom: '1px solid #cfdaf6', background: '#e8fde8', color: '#1f8a4c', fontSize: 13 }}>
              Workflow completed
            </div>
          )}
          {workflowExecuteStatus && workflowSessionActive && workflowExecuteStatus.status !== 'finished' && workflowExecuteStatus.status !== 'error' && workflowExecuteStatus.status !== 'terminated' && (
            <div style={{ padding: '8px 12px', borderBottom: '1px solid #cfdaf6', background: '#f7f9ff', fontSize: 13 }}>
              Workflow status: {workflowExecuteStatus.status}
              {workflowExecuteStatus.error ? ` - ${workflowExecuteStatus.error}` : ''}
            </div>
          )}
          <div style={{ flex: 1, minHeight: 0, background: '#0b1220' }}>
            <iframe
              key={liveSessionName}
              src={`/terminal?session=${encodeURIComponent(liveSessionName)}&compact=1`}
              style={{ width: '100%', height: '100%', border: 'none' }}
            />
          </div>
          {workflowSessionActive && workflowExecuteStatus?.waiting_for_continue && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '10px 14px', borderTop: '1px solid #cfdaf6', background: '#f7f9ff' }}>
              <Button size="xs" variant="light" onClick={onContinueWorkflow} loading={continuingWorkflow}>
                Continue Next Node
              </Button>
            </div>
          )}
        </div>
      ) : (
        <>
          <div style={{ padding: '10px 14px 0 14px' }}>
            {newSessionWorkflow && (
              <Text size="xs" color="dimmed" mb={8}>
                Workflow mode: {`core/workflows/${newSessionWorkflow}`}
              </Text>
            )}
            {!hideSessionRootSelect && hasSessionWorktrees && (
              <Select
                label="Worktree"
                placeholder="Choose where to start"
                value={selectedSessionPath || null}
                onChange={(value) => setSelectedSessionPath(value || '')}
                data={sessionRootOptions.map((root) => ({ value: root.value, label: root.label }))}
                size="xs"
                mb={8}
              />
            )}
          </div>
          <div style={{ flex: 1, minHeight: 0, padding: '0 14px 14px 14px' }}>
            <Textarea
              placeholder="What would you like to do?"
              value={sessionPromptText}
              onChange={(event) => setSessionPromptText(event.currentTarget.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
                  onStart(hideSessionRootSelect ? undefined : (selectedSessionPath || undefined));
                }
              }}
              autosize={false}
              minRows={1}
              styles={{
                root: { height: '100%' },
                wrapper: { height: '100%' },
                input: {
                  height: '100%',
                  minHeight: '100%',
                  resize: 'none',
                  border: 'none',
                  padding: 0,
                  background: 'transparent',
                  fontSize: 14,
                  lineHeight: 1.6,
                },
              }}
            />
          </div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
              padding: '10px 14px',
              borderTop: '1px solid #cfdaf6',
              background: '#f7f9ff',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                <input type="checkbox" checked={newSessionSandbox} onChange={(event) => setNewSessionSandbox(event.currentTarget.checked)} />
                <span>Sandbox</span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                <input type="checkbox" checked={newSessionAuto} onChange={(event) => setNewSessionAuto(event.currentTarget.checked)} />
                <span>Auto Run (Yolo)</span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                <input type="checkbox" checked={newSessionNetwork} onChange={(event) => setNewSessionNetwork(event.currentTarget.checked)} />
                <span>Network Access</span>
              </label>
              {newSessionWorkflow && (
                <>
                  <Select
                    value={newSessionNextNodeTrigger}
                    onChange={(value) => setNewSessionNextNodeTrigger((value as NextNodeTrigger) || 'auto_continue')}
                    data={[
                      { value: 'auto_continue', label: 'Auto continue' },
                      { value: 'start_by_prompt', label: 'Start by prompt' },
                    ]}
                    size="xs"
                    style={{ width: 160 }}
                  />
                  {newSessionWorkflowResumeAvailable && (
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                      <input type="checkbox" checked={newSessionWorkflowResume} onChange={(event) => setNewSessionWorkflowResume(event.currentTarget.checked)} />
                      <span>Resume Workflow</span>
                    </label>
                  )}
                </>
              )}
            </div>
            <Button
              onClick={() => onStart(hideSessionRootSelect ? undefined : (selectedSessionPath || undefined))}
              disabled={!sessionPromptText.trim() || startingSession}
              loading={startingSession}
            >
              Start
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
