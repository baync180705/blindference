import { useState, useEffect } from 'react';
import { BrowserProvider } from 'ethers';

export function useWeb3() {
  const [address, setAddress] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [jwt, setJwt] = useState<string | null>(localStorage.getItem('token'));
  const [role, setRole] = useState<string | null>(localStorage.getItem('role'));
  const [isRegistrationNeeded, setIsRegistrationNeeded] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Restore session
  useEffect(() => {
    if (jwt && address === null) {
      const storedAddress = localStorage.getItem('address');
      if (storedAddress) {
        setAddress(storedAddress);
      }
    }
  }, [jwt, address]);

  const connect = async () => {
    setIsConnecting(true);
    setAuthError(null);
    try {
      if (!(window as any).ethereum) {
        throw new Error("No crypto wallet found. Please install it.");
      }

      // Initialize provider and request accounts
      const provider = new BrowserProvider((window as any).ethereum);
      const accounts = await provider.send("eth_requestAccounts", []);
      const userAddress = accounts[0];

      // Call backend to login
      const response = await fetch("http://localhost:8000/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address: userAddress }),
      });

      if (response.ok) {
        const data = await response.json();
        setAddress(userAddress);
        setJwt(data.access_token);
        setRole(data.role);
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("role", data.role);
        localStorage.setItem("address", userAddress);
      } else if (response.status === 404) {
        // Need to register
        setAddress(userAddress);
        setIsRegistrationNeeded(true);
      } else {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to login");
      }
    } catch (err: any) {
      console.error(err);
      setAuthError(err.message || "Connection failed");
    } finally {
      setIsConnecting(false);
    }
  };

  const register = async (selectedRole: string) => {
    if (!address) return;
    setIsConnecting(true);
    setAuthError(null);
    try {
      const response = await fetch("http://localhost:8000/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address, role: selectedRole }),
      });

      if (response.ok) {
        const data = await response.json();
        setJwt(data.access_token);
        setRole(data.role);
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("role", data.role);
        localStorage.setItem("address", address);
        setIsRegistrationNeeded(false);
      } else {
        const errData = await response.json();
        throw new Error(errData.detail || "Registration failed");
      }
    } catch (err: any) {
      console.error(err);
      setAuthError(err.message || "Registration failed");
    } finally {
      setIsConnecting(false);
    }
  };

  const disconnect = () => {
    setAddress(null);
    setJwt(null);
    setRole(null);
    localStorage.removeItem("token");
    localStorage.removeItem("address");
    localStorage.removeItem("role");
  };

  return { address, isConnecting, authError, isRegistrationNeeded, connect, register, disconnect, jwt, role, setIsRegistrationNeeded };
}
