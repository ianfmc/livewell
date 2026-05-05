import { createContext, useMemo, type ReactNode } from 'react';
import { MessageProcessor } from '@a2ui/web_core/v0_9';
import { basicCatalog, type ReactComponentImplementation } from '@a2ui/react/v0_9';

export const A2uiContext = createContext<MessageProcessor<ReactComponentImplementation> | null>(null);

export function A2uiProvider({ children }: { children: ReactNode }) {
  const processor = useMemo(
    () => new MessageProcessor<ReactComponentImplementation>([basicCatalog]),
    []
  );
  return <A2uiContext.Provider value={processor}>{children}</A2uiContext.Provider>;
}
