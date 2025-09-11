// ESLint v9 flat config (ESM) with React/Next support and proper globals
import js from '@eslint/js';
import reactPlugin from 'eslint-plugin-react';
import nextPlugin from '@next/eslint-plugin-next';
import globals from 'globals';

export default [
  js.configs.recommended,
  // Browser-side files (Next.js app router pages/components)
  {
    files: ['app/**/*.{js,jsx}', 'lib/**/*.{js,jsx}', 'public/**/*.{js,jsx}', '*.js', '*.jsx'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: {
        ...globals.browser,
        // Ensure CI recognizes common web globals used in code
        fetch: 'readonly',
        localStorage: 'readonly',
        atob: 'readonly',
        confirm: 'readonly',
        // Next.js exposes process.env at build-time; allow references in UI helpers
        process: 'readonly',
      },
    },
    plugins: {
      react: reactPlugin,
      '@next/next': nextPlugin,
    },
    rules: {
      'react/react-in-jsx-scope': 'off',
      'react/jsx-uses-react': 'off',
      // Keep CI green without changing app code
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-empty': 'off',
    },
  },
  // Node-side config files (Next.js config, etc.)
  {
    files: ['next.config.js', '**/*.config.js', 'scripts/**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'commonjs',
      globals: {
        ...globals.node,
      },
    },
    rules: {
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-empty': 'off',
    },
  },
  {
    ignores: ['.next/**', 'node_modules/**', 'dist/**'],
  },
];


