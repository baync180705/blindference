import { useState, useEffect } from 'react';

export function useWeb3() {
  const [address, setAddress] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);

  const connect = async () => {
    setIsConnecting(true);
    // Mock connection
    await new globalThis.Promise(resolve => setTimeout(resolve, 1000));
    setAddress("0x32Be343B94f860124dC4fEe278FDCBD38C102D88");
    setIsConnecting(false);
  };

  const disconnect = () => {
    setAddress(null);
  };

  return { address, isConnecting, connect, disconnect };
}
