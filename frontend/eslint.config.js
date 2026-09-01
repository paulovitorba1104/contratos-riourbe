import js from "@eslint/js";
import tseslint from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";

export default [
  { ignores: ["dist", "node_modules"] },
  js.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 2020,
      sourceType: "module",
      globals: {
        window: "readonly",
        document: "readonly",
        fetch: "readonly",
        console: "readonly",
        URL: "readonly",
        RequestInit: "readonly",
        localStorage: "readonly",
        sessionStorage: "readonly",
      },
    },
    plugins: {
      "@typescript-eslint": tseslint,
    },
    rules: {
      ...tseslint.configs.recommended.rules,
      // TypeScript já cobre variáveis/tipos não definidos com mais precisão
      // (inclusive tipos ambientes como React.ReactNode) — no-undef do ESLint
      // dá falso positivo nesses casos.
      "no-undef": "off",
    },
  },
  {
    files: ["vite.config.ts"],
    languageOptions: {
      globals: {
        process: "readonly",
      },
    },
  },
];
