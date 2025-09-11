// Minimal ESLint v9 flat config to enable linting in CI without extra rules
// This satisfies ESLint's required config and ignores build/artifact folders.

export default [
  {
    files: ["**/*.{js,jsx}"],
    ignores: [".next/**", "node_modules/**", "dist/**"],
  },
];


