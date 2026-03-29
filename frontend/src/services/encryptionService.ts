import { cofhejs, Encryptable } from 'cofhejs/web';
import { BrowserProvider } from 'ethers';

export const initializeEncryption = async (provider: any) => {
  const browserProvider = new BrowserProvider(provider);
  const signer = await browserProvider.getSigner();
  try {
    const res = await cofhejs.initializeWithEthers({
        ethersProvider: browserProvider,
        ethersSigner: signer,
        environment: "TESTNET",
        generatePermit: false // Prevent failures related to unnecessary Permit generation
    });
    console.log("Initialization result:", res);
    if (!res.success) {
      console.error("Initialization Failed:", res.error);
    }
  } catch(e) {
    console.log("Exception:", e);
    throw e;
  }
};

export const encryptRow = async (row: any, columns: string[]) => {
  const encryptableRow = columns.map(col => {
    const val = row[col];
    let num = parseInt(val);
    if (isNaN(num)) num = 0;
    return Encryptable.uint64(BigInt(num));
  });

  const res=await cofhejs.encrypt(encryptableRow, () => {});
  if(!res.success){
    throw new Error(res.error?.message || "Encryption failed");
  }
  return res.data;
};
