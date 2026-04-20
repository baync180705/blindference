import rawInit, * as tfheModule from '../../node_modules/tfhe/tfhe.js'
import wasmUrl from '../../node_modules/tfhe/tfhe_bg.wasm?url'

export * from '../../node_modules/tfhe/tfhe.js'

type InitArgument =
  | {
      module_or_path?: RequestInfo | URL | Response | BufferSource | WebAssembly.Module | Promise<unknown>
      memory?: WebAssembly.Memory
      thread_stack_size?: number
    }
  | RequestInfo
  | URL
  | Response
  | BufferSource
  | WebAssembly.Module
  | Promise<unknown>
  | undefined

export default async function init(moduleOrPath?: InitArgument) {
  if (moduleOrPath && Object.getPrototypeOf(moduleOrPath) === Object.prototype) {
    const typedArg = moduleOrPath as {
      module_or_path?: unknown
      memory?: WebAssembly.Memory
      thread_stack_size?: number
    }
    return rawInit({
      module_or_path: typedArg.module_or_path ?? wasmUrl,
      memory: typedArg.memory,
      thread_stack_size: typedArg.thread_stack_size,
    })
  }

  return rawInit({
    module_or_path: moduleOrPath ?? wasmUrl,
  })
}

export const __tfheModule = tfheModule
