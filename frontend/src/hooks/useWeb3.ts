import { useEffect, useState } from 'react';
import { BrowserProvider, Contract, JsonRpcSigner } from 'ethers';
import type { FhenixClient } from 'fhenixjs';
import blindInferenceArtifact from '../contracts/abis/BlindInference.json';
import inferenceEngineArtifact from '../contracts/abis/InferenceEngine.json';
import modelRegistryArtifact from '../contracts/abis/ModelRegistry.json';
import paymentEscrowArtifact from '../contracts/abis/PaymentEscrow.json';

declare global {
  interface Window {
    ethereum?: {
      request(args: { method: string; params?: unknown[] }): Promise<unknown>;
    };
  }
}

type ContractArtifact = {
  abi: unknown[];
};

type Web3Contracts = {
  blindInference: Contract | null;
  inferenceEngine: Contract | null;
  modelRegistry: Contract | null;
  paymentEscrow: Contract | null;
};

const contractArtifacts = {
  blindInference: blindInferenceArtifact as ContractArtifact,
  inferenceEngine: inferenceEngineArtifact as ContractArtifact,
  modelRegistry: modelRegistryArtifact as ContractArtifact,
  paymentEscrow: paymentEscrowArtifact as ContractArtifact,
};

const blindInferenceAddress = import.meta.env.VITE_BLIND_INFERENCE_ADDRESS as string | undefined;
const inferenceEngineAddress =
  (import.meta.env.VITE_INFERENCE_ENGINE_ADDRESS as string | undefined) ?? blindInferenceAddress;
const modelRegistryAddress = import.meta.env.VITE_MODEL_REGISTRY_ADDRESS as string | undefined;
const paymentEscrowAddress = import.meta.env.VITE_PAYMENT_ESCROW_ADDRESS as string | undefined;

async function createFhenixClient() {
  const runtimeEntry = '/vendor/fhenixjs/fhenix.js';
  const module = await import(/* @vite-ignore */ runtimeEntry);
  return new module.FhenixClient({ provider: window.ethereum! });
}

function buildContracts(signer: JsonRpcSigner): Web3Contracts {
  return {
    blindInference: blindInferenceAddress
      ? new Contract(blindInferenceAddress, contractArtifacts.blindInference.abi, signer)
      : null,
    inferenceEngine: inferenceEngineAddress
      ? new Contract(inferenceEngineAddress, contractArtifacts.inferenceEngine.abi, signer)
      : null,
    modelRegistry: modelRegistryAddress
      ? new Contract(modelRegistryAddress, contractArtifacts.modelRegistry.abi, signer)
      : null,
    paymentEscrow: paymentEscrowAddress
      ? new Contract(paymentEscrowAddress, contractArtifacts.paymentEscrow.abi, signer)
      : null,
  };
}

export function useWeb3() {
  const [address, setAddress] = useState<string | null>(null);
  const [provider, setProvider] = useState<BrowserProvider | null>(null);
  const [signer, setSigner] = useState<JsonRpcSigner | null>(null);
  const [fhenixClient, setFhenixClient] = useState<FhenixClient | null>(null);
  const [contracts, setContracts] = useState<Web3Contracts>({
    blindInference: null,
    inferenceEngine: null,
    modelRegistry: null,
    paymentEscrow: null,
  });
  const [isConnecting, setIsConnecting] = useState(false);

  useEffect(() => {
    let isActive = true;

    async function hydrateAuthorizedAccount() {
      if (!window.ethereum) {
        return;
      }

      const accounts = await window.ethereum.request({ method: 'eth_accounts' }) as string[];
      if (accounts.length === 0 || !isActive) {
        return;
      }

      const nextProvider = new BrowserProvider(window.ethereum);
      const nextSigner = await nextProvider.getSigner();
      const nextClient = await createFhenixClient();

      if (!isActive) {
        return;
      }

      setAddress(accounts[0]);
      setProvider(nextProvider);
      setSigner(nextSigner);
      setFhenixClient(nextClient);
      setContracts(buildContracts(nextSigner));
    }

    hydrateAuthorizedAccount().catch((error) => {
      console.error('Failed to hydrate wallet state:', error);
    });

    return () => {
      isActive = false;
    };
  }, []);

  const connect = async () => {
    if (!window.ethereum) {
      throw new Error('No injected wallet found');
    }

    setIsConnecting(true);
    try {
      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' }) as string[];
      const nextProvider = new BrowserProvider(window.ethereum);
      const nextSigner = await nextProvider.getSigner();
      const nextClient = await createFhenixClient();
      const nextContracts = buildContracts(nextSigner);

      setAddress(accounts[0] ?? null);
      setProvider(nextProvider);
      setSigner(nextSigner);
      setFhenixClient(nextClient);
      setContracts(nextContracts);

      return {
        address: accounts[0] ?? null,
        provider: nextProvider,
        signer: nextSigner,
        fhenixClient: nextClient,
        contracts: nextContracts,
      };
    } finally {
      setIsConnecting(false);
    }
  };

  const disconnect = () => {
    setAddress(null);
    setProvider(null);
    setSigner(null);
    setFhenixClient(null);
    setContracts({
      blindInference: null,
      inferenceEngine: null,
      modelRegistry: null,
      paymentEscrow: null,
    });
  };

  return {
    address,
    provider,
    signer,
    fhenixClient,
    contracts,
    isConnecting,
    connect,
    disconnect,
    abis: {
      blindInference: contractArtifacts.blindInference.abi,
      inferenceEngine: contractArtifacts.inferenceEngine.abi,
      modelRegistry: contractArtifacts.modelRegistry.abi,
      paymentEscrow: contractArtifacts.paymentEscrow.abi,
    },
    artifacts: contractArtifacts,
  };
}
