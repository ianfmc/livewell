import { useContext } from 'react';
import type { MessageProcessor } from '@a2ui/web_core/v0_9';
import type { ReactComponentImplementation } from '@a2ui/react/v0_9';
import { A2uiContext } from './A2uiProvider';

export function useA2ui(): MessageProcessor<ReactComponentImplementation> {
  const ctx = useContext(A2uiContext);
  if (!ctx) throw new Error('useA2ui must be used inside <A2uiProvider>');
  return ctx;
}
