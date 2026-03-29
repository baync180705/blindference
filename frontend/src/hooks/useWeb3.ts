import { useState } from 'react';
import blindInferenceArtifact from '../contracts/abis/BlindInference.json';
import modelRegistryArtifact from '../contracts/abis/ModelRegistry.json';
import paymentEscrowArtifact from '../contracts/abis/PaymentEscrow.json';

type ContractArtifact = {
  abi: unknown[];
};

const contractArtifacts = {
  blindInference: blindInferenceArtifact as ContractArtifact,
  modelRegistry: modelRegistryArtifact as ContractArtifact,
  paymentEscrow: paymentEscrowArtifact as ContractArtifact,
};

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

  return {
    address,
    isConnecting,
    connect,
    disconnect,
    abis: {
      blindInference: contractArtifacts.blindInference.abi,
      modelRegistry: contractArtifacts.modelRegistry.abi,
      paymentEscrow: contractArtifacts.paymentEscrow.abi,
    },
    artifacts: contractArtifacts,
  };
}
