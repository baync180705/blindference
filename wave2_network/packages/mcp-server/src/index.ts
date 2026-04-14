import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'

const server = new McpServer({
  name: 'blindference-wave2-mcp',
  version: '0.1.0',
})

server.registerTool(
  'get_node_metrics',
  {
    description: 'Return mock node metrics for the scaffolded MCP server.',
    inputSchema: {},
  },
  async () => ({
    content: [
      {
        type: 'text',
        text: JSON.stringify({
          address: '0xstub',
          reputation: 85,
          status: 'mock',
        }),
      },
    ],
  }),
)

server.registerTool(
  'list_models',
  {
    description: 'Return mock model data for the scaffolded MCP server.',
    inputSchema: {},
  },
  async () => ({
    content: [
      {
        type: 'text',
        text: JSON.stringify([
          {
            modelId: 'stub-model',
            tier: 0,
            status: 'mock',
          },
        ]),
      },
    ],
  }),
)

async function main() {
  const transport = new StdioServerTransport()
  await server.connect(transport)
}

main().catch((error) => {
  console.error('MCP server failed to start', error)
  process.exit(1)
})
