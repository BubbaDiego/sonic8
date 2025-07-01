import { expect } from 'vitest';
import matchers from '@testing-library/jest-dom/matchers';

expect.extend(matchers);

// Ensure import.meta.env is defined for tests
if (!globalThis.import) {
  globalThis.import = { meta: { env: {} } };
} else if (!globalThis.import.meta) {
  globalThis.import.meta = { env: {} };
} else if (!globalThis.import.meta.env) {
  globalThis.import.meta.env = {};
}
