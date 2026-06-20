import { setupServer } from 'msw/node'

// Default empty handler list — tests add their own handlers
export const server = setupServer()
