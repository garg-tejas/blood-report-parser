import nextVitals from "eslint-config-next/core-web-vitals"
const config = [
  { ignores: ["node_modules/**", ".next/**", "out/**", "build/**"] },
  ...nextVitals,
]
export default config
