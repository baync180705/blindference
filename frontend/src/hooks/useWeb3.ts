import { createContext, createElement, ReactNode, useContext, useEffect, useMemo, useState } from 'react';
import { BrowserProvider, Contract, JsonRpcSigner } from 'ethers';
import type { FhenixClient } from 'fhenixjs';
import blindInferenceArtifact from '../../../fhenix_inference/artifacts/contracts/BlindInference.sol/BlindInference.json';
import inferenceEngineArtifact from '../../../fhenix_inference/artifacts/contracts/InferenceEngine.sol/InferenceEngine.json';
import modelRegistryArtifact from '../../../fhenix_inference/artifacts/contracts/ModelRegistry.sol/ModelRegistry.json';
import paymentEscrowArtifact from '../../../fhenix_inference/artifacts/contracts/PaymentEscrow.sol/PaymentEscrow.json';

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

type Web3ContextValue = {
  address: string | null;
  provider: BrowserProvider | null;
  signer: JsonRpcSigner | null;
  fhenixClient: FhenixClient | null;
  connectionError: string | null;
  contracts: Web3Contracts;
  isConnecting: boolean;
  connect: () => Promise<{
    address: string | null;
    provider: BrowserProvider;
    signer: JsonRpcSigner;
    fhenixClient: FhenixClient | null;
    contracts: Web3Contracts;
  }>;
  disconnect: () => void;
  abis: {
    blindInference: unknown[];
    inferenceEngine: unknown[];
    modelRegistry: unknown[];
    paymentEscrow: unknown[];
  };
  artifacts: typeof contractArtifacts;
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

const defaultContracts: Web3Contracts = {
  blindInference: null,
  inferenceEngine: null,
  modelRegistry: null,
  paymentEscrow: null,
};

const Web3Context = createContext<Web3ContextValue | null>(null);

async function createFhenixClient(provider: BrowserProvider) {
  const runtimeUrl = new URL('/vendor/fhenixjs/fhenix.esm.js', window.location.origin).href;
  const module = await import(/* @vite-ignore */ runtimeUrl);
  return new module.FhenixClient({ provider });
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

export function Web3Provider({ children }: { children: ReactNode }) {
  const [address, setAddress] = useState<string | null>(null);
  const [provider, setProvider] = useState<BrowserProvider | null>(null);
  const [signer, setSigner] = useState<JsonRpcSigner | null>(null);
  const [fhenixClient, setFhenixClient] = useState<FhenixClient | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [contracts, setContracts] = useState<Web3Contracts>(defaultContracts);
  const [isConnecting, setIsConnecting] = useState(false);

  async function initializeFhenixClient(nextProvider: BrowserProvider) {
    try {
      const nextClient = await createFhenixClient(nextProvider);
      setFhenixClient(nextClient);
      setConnectionError(null);
      return nextClient;
    } catch (error) {
      console.error('Failed to initialize Fhenix client:', error);
      setFhenixClient(null);
      setConnectionError(
        error instanceof Error
          ? `Wallet connected, but the Fhenix client failed to initialize: ${error.message}`
          : 'Wallet connected, but the Fhenix client failed to initialize.',
      );
      return null;
    }
  }

  useEffect(() => {
    let isActive = true;

    async function hydrateAuthorizedAccount() {
      if (!window.ethereum) {
        return;
      }

      const accounts = (await window.ethereum.request({ method: 'eth_accounts' })) as string[];
      if (accounts.length === 0 || !isActive) {
        return;
      }

      const nextProvider = new BrowserProvider(window.ethereum);
      const nextSigner = await nextProvider.getSigner();

      if (!isActive) {
        return;
      }

      setAddress(accounts[0]);
      setProvider(nextProvider);
      setSigner(nextSigner);
      setContracts(buildContracts(nextSigner));
      void initializeFhenixClient(nextProvider);
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
    setConnectionError(null);
    try {
      const accounts = (await window.ethereum.request({ method: 'eth_requestAccounts' })) as string[];
      const nextProvider = new BrowserProvider(window.ethereum);
      const nextSigner = await nextProvider.getSigner();
      const nextContracts = buildContracts(nextSigner);
      const nextAddress = accounts[0] ?? null;

      setAddress(nextAddress);
      setProvider(nextProvider);
      setSigner(nextSigner);
      setContracts(nextContracts);

      const nextClient = await initializeFhenixClient(nextProvider);

      return {
        address: nextAddress,
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
    setConnectionError(null);
    setContracts(defaultContracts);
  };

  const value = useMemo<Web3ContextValue>(
    () => ({
      address,
      provider,
      signer,
      fhenixClient,
      connectionError,
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
    }),
    [address, provider, signer, fhenixClient, connectionError, contracts, isConnecting],
  );

  return createElement(Web3Context.Provider, { value }, children);
}

export function useWeb3() {
  const context = useContext(Web3Context);
  if (!context) {
    throw new Error('useWeb3 must be used within a Web3Provider');
  }
  return context;
}
