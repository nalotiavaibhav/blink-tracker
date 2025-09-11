// Minimal ESLint v9 flat config (ESM) for CI
export default [
  {
    files: ["**/*.{js,jsx}"],
    ignores: [".next/**", "node_modules/**", "dist/**"],
  },
];


