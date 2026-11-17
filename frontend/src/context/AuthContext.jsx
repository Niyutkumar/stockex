/* Who is logged in, available to the whole app.
 *
 * React Context exists so that a component deep in the tree can read the
 * current user without every component in between passing it down.
 */

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // "loading" until we know, so the app does not flash the login screen
  // at someone who is already signed in.
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    let cancelled = false;

    async function restore() {
      if (!getToken()) {
        setStatus("anonymous");
        return;
      }
      try {
        // A stored token proves nothing — it may have expired or been
        // signed with a different secret. Ask the server.
        const me = await api.me();
        if (!cancelled) {
          setUser(me);
          setStatus("authenticated");
        }
      } catch {
        setToken(null);
        if (!cancelled) setStatus("anonymous");
      }
    }

    restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email, password) => {
    const { access_token } = await api.login(email, password);
    setToken(access_token);
    const me = await api.me();
    setUser(me);
    setStatus("authenticated");
    return me;
  }, []);

  const register = useCallback(
    async (payload) => {
      await api.register(payload);
      // Straight into the app rather than bouncing to a login form.
      return login(payload.email, payload.password);
    },
    [login]
  );

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setStatus("anonymous");
  }, []);

  return (
    <AuthContext.Provider value={{ user, status, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
