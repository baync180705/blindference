import { cofhejs, Encryptable } from 'cofhejs/web';
import { BrowserProvider } from 'ethers';

export const initializeEncryption = async (provider: any) => {
  const browserProvider = new BrowserProvider(provider);
  const signer = await browserProvider.getSigner();
  try{
  await cofhejs.initializeWithEthers({
      ethersProvider: browserProvider,
      ethersSigner: signer,
      environment: "TESTNET"
  });}
  catch(e){
    console.log(e);
  }
};

export const encryptRow = async (row: any, columns: string[]) => {
  const encryptableRow = columns.map(col => {
    const val = row[col];
    let num = parseInt(val);
    if (isNaN(num)) num = 0;
    return Encryptable.uint64(BigInt(num));
  });

  return await cofhejs.encrypt(encryptableRow, () => {});
};
