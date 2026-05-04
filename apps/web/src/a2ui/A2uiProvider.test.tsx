import { describe, it, expect } from 'vitest';
import { render, renderHook } from '@testing-library/react';
import React from 'react';
import { A2uiProvider } from './A2uiProvider';
import { useA2ui } from './useA2ui';

describe('A2uiProvider', () => {
  it('provides a MessageProcessor to children via useA2ui', () => {
    const { result } = renderHook(() => useA2ui(), {
      wrapper: ({ children }) => <A2uiProvider>{children}</A2uiProvider>,
    });
    expect(result.current).toBeDefined();
    expect(typeof result.current.processMessages).toBe('function');
  });

  it('useA2ui throws when used outside A2uiProvider', () => {
    expect(() => {
      renderHook(() => useA2ui());
    }).toThrow('useA2ui must be used inside <A2uiProvider>');
  });

  it('provider renders children', () => {
    const { getByText } = render(
      <A2uiProvider>
        <span>hello</span>
      </A2uiProvider>
    );
    expect(getByText('hello')).toBeDefined();
  });
});
