import { createContext, createElement, ReactNode, useContext, useEffect, useMemo, useState } from 'react';
import { BrowserProvider, Contract, JsonRpcSigner } from 'ethers';
import type { CofheClient } from '@cofhe/sdk';
import blindInferenceArtifact from '../../../fhenix_inference/artifacts/contracts/BlindInference.sol/BlindInference.json';
import inferenceEngineArtifact from '../../../fhenix_inference/artifacts/contracts/InferenceEngine.sol/InferenceEngine.json';
import modelRegistryArtifact from '../../../fhenix_inference/artifacts/contracts/ModelRegistry.sol/ModelRegistry.json';
import paymentEscrowArtifact from '../../../fhenix_inference/artifacts/contracts/PaymentEscrow.sol/PaymentEscrow.json';
import paymentTokenArtifact from '../contracts/abis/MockERC20.json';

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
  paymentToken: Contract | null;
};

type Web3ContextValue = {
  address: string | null;
  provider: BrowserProvider | null;
  signer: JsonRpcSigner | null;
  fhenixClient: CofheClient | null;
  connectionError: string | null;
  contracts: Web3Contracts;
  paymentTokenAddress: string | null;
  inferenceEngineAddress: string | null;
  isConnecting: boolean;
  isInitializingFhe: boolean;
  connect: () => Promise<{
    address: string | null;
    provider: BrowserProvider;
    signer: JsonRpcSigner;
    fhenixClient: CofheClient | null;
    contracts: Web3Contracts;
  }>;
  ensureFhenixClient: () => Promise<CofheClient>;
  disconnect: () => void;
  abis: {
    blindInference: unknown[];
    inferenceEngine: unknown[];
    modelRegistry: unknown[];
    paymentEscrow: unknown[];
    paymentToken: unknown[];
  };
  artifacts: typeof contractArtifacts;
};

const contractArtifacts = {
  blindInference: blindInferenceArtifact as ContractArtifact,
  inferenceEngine: inferenceEngineArtifact as ContractArtifact,
  modelRegistry: modelRegistryArtifact as ContractArtifact,
  paymentEscrow: paymentEscrowArtifact as ContractArtifact,
  paymentToken: paymentTokenArtifact as ContractArtifact,
};

const blindInferenceAddress = import.meta.env.VITE_BLIND_INFERENCE_ADDRESS as string | undefined;
const inferenceEngineAddress =
  (import.meta.env.VITE_INFERENCE_ENGINE_ADDRESS as string | undefined) ?? blindInferenceAddress;
const modelRegistryAddress = import.meta.env.VITE_MODEL_REGISTRY_ADDRESS as string | undefined;
const paymentEscrowAddress = import.meta.env.VITE_PAYMENT_ESCROW_ADDRESS as string | undefined;
const paymentTokenAddress = import.meta.env.VITE_PAYMENT_TOKEN_ADDRESS as string | undefined;

const defaultContracts: Web3Contracts = {
  blindInference: null,
  inferenceEngine: null,
  modelRegistry: null,
  paymentEscrow: null,
  paymentToken: null,
};

const Web3Context = createContext<Web3ContextValue | null>(null);
const SEPOLIA_CHAIN_ID = 11155111n;
const SEPOLIA_CHAIN_ID_HEX = '0xaa36a7';

async function ensureSepoliaNetwork(provider: BrowserProvider) {
  const network = await provider.getNetwork();
  if (network.chainId === SEPOLIA_CHAIN_ID) {
    return;
  }

  if (!window.ethereum) {
    throw new Error('MetaMask is required to switch to Sepolia');
  }

  try {
    await window.ethereum.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: SEPOLIA_CHAIN_ID_HEX }],
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : '';
    throw new Error(
      message.includes('4902')
        ? 'Sepolia is not available in MetaMask. Add the Sepolia network and try again.'
        : 'Wrong network detected. Switch MetaMask to Ethereum Sepolia and reconnect.',
    );
  }

  const refreshedNetwork = await provider.getNetwork();
  if (refreshedNetwork.chainId !== SEPOLIA_CHAIN_ID) {
    throw new Error('Wrong network detected. Switch MetaMask to Ethereum Sepolia and reconnect.');
  }
}

async function createFhenixClient(provider: BrowserProvider, signer: JsonRpcSigner) {
  await ensureSepoliaNetwork(provider);

  const [{ Ethers6Adapter }, { chains }, { createCofheClient, createCofheConfig }] = await Promise.all([
    import('@cofhe/sdk/adapters'),
    import('@cofhe/sdk/chains'),
    import('@cofhe/sdk/web'),
  ]);

  const config = createCofheConfig({
    supportedChains: [chains.sepolia],
  });
  const client = createCofheClient(config);
  const { publicClient, walletClient } = await Ethers6Adapter(provider, signer);
  await client.connect(publicClient, walletClient);

  return client;
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
    paymentToken: paymentTokenAddress
      ? new Contract(paymentTokenAddress, contractArtifacts.paymentToken.abi, signer)
      : null,
  };
}

export function Web3Provider({ children }: { children: ReactNode }) {
  const [address, setAddress] = useState<string | null>(null);
  const [provider, setProvider] = useState<BrowserProvider | null>(null);
  const [signer, setSigner] = useState<JsonRpcSigner | null>(null);
  const [fhenixClient, setFhenixClient] = useState<CofheClient | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [contracts, setContracts] = useState<Web3Contracts>(defaultContracts);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isInitializingFhe, setIsInitializingFhe] = useState(false);

  async function initializeFhenixClient(nextProvider: BrowserProvider, nextSigner: JsonRpcSigner) {
    setIsInitializingFhe(true);
    try {
      const nextClient = await createFhenixClient(nextProvider, nextSigner);
      setFhenixClient(nextClient);
      setConnectionError(null);
      return nextClient;
    } catch (error) {
      console.error('Failed to initialize Fhenix client:', error);
      setFhenixClient(null);
      setConnectionError(
        error instanceof Error
          ? error.message
          : 'Wallet connected, but the Fhenix client failed to initialize.',
      );
      return null;
    } finally {
      setIsInitializingFhe(false);
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

      let nextProvider = new BrowserProvider(window.ethereum);
      await ensureSepoliaNetwork(nextProvider);
      nextProvider = new BrowserProvider(window.ethereum);
      const nextSigner = await nextProvider.getSigner();

      if (!isActive) {
        return;
      }

      setAddress(accounts[0]);
      setProvider(nextProvider);
      setSigner(nextSigner);
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
    setConnectionError(null);
    try {
      const accounts = (await window.ethereum.request({ method: 'eth_requestAccounts' })) as string[];
      let nextProvider = new BrowserProvider(window.ethereum);
      await ensureSepoliaNetwork(nextProvider);
      nextProvider = new BrowserProvider(window.ethereum);
      const nextSigner = await nextProvider.getSigner();
      const nextContracts = buildContracts(nextSigner);
      const nextAddress = accounts[0] ?? null;

      setAddress(nextAddress);
      setProvider(nextProvider);
      setSigner(nextSigner);
      setContracts(nextContracts);

      return {
        address: nextAddress,
        provider: nextProvider,
        signer: nextSigner,
        fhenixClient: null,
        contracts: nextContracts,
      };
    } finally {
      setIsConnecting(false);
    }
  };

  const ensureFhenixClient = async () => {
    if (fhenixClient) {
      return fhenixClient;
    }

    if (!provider || !signer) {
      throw new Error('Connect your wallet before initializing Fhenix');
    }

    const nextClient = await initializeFhenixClient(provider, signer);
    if (!nextClient) {
      throw new Error('Fhenix client could not be initialized');
    }

    return nextClient;
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
      paymentTokenAddress: paymentTokenAddress ?? null,
      inferenceEngineAddress: inferenceEngineAddress ?? null,
      isConnecting,
      isInitializingFhe,
      connect,
      ensureFhenixClient,
      disconnect,
      abis: {
        blindInference: contractArtifacts.blindInference.abi,
        inferenceEngine: contractArtifacts.inferenceEngine.abi,
        modelRegistry: contractArtifacts.modelRegistry.abi,
        paymentEscrow: contractArtifacts.paymentEscrow.abi,
        paymentToken: contractArtifacts.paymentToken.abi,
      },
      artifacts: contractArtifacts,
    }),
    [address, provider, signer, fhenixClient, connectionError, contracts, isConnecting, isInitializingFhe],
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
