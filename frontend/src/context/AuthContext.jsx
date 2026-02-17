import React, { createContext, useContext } from 'react';
import { useAuth } from '../hooks/useAuth';

const AuthContext = createContext(null);

/**
 * Provider that wraps children with authentication state.
 * Delegates all auth logic to the useAuth hook.
 */
export function AuthProvider({ children }) {
  const authState = useAuth();

  return (
    <AuthContext.Provider value={authState}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Hook to access the current auth context.
 *
 * @returns {{ user: object|null, loading: boolean, isSuperAdmin: boolean }}
 */
export function useAuthContext() {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
}
