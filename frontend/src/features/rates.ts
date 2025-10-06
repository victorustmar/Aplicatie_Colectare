// cheile TREBUIE să fie identice cu backendul
export const PORTABLE_KEYS = [
  "portable_pastila",
  "portable_0_50",
  "portable_51_150",
  "portable_151_250",
  "portable_251_500",
  "portable_501_750",
  "portable_751_1000",
  "portable_1000_plus",
] as const;

export const KG_KEYS = [
  "auto_3a",
  "auto_3b",
  "auto_3c",
  "industrial_4a",
  "industrial_4b",
  "industrial_4c",
] as const;

export type PortableKey = typeof PORTABLE_KEYS[number];
export type KgKey = typeof KG_KEYS[number];

export const LABELS: Record<string, string> = {
  portable_pastila: "Pastilă",
  portable_0_50: "0–50 g",
  portable_51_150: "51–150 g",
  portable_151_250: "151–250 g",
  portable_251_500: "251–500 g",
  portable_501_750: "501–750 g",
  portable_751_1000: "751–1000 g",
  portable_1000_plus: "> 1000 g",
  auto_3a: "Auto 3a",
  auto_3b: "Auto 3b",
  auto_3c: "Auto 3c",
  industrial_4a: "Industrial 4a",
  industrial_4b: "Industrial 4b",
  industrial_4c: "Industrial 4c",
};

// tarife RON (aceleași ca pe server)
export const PORTABLE_RATES: Record<PortableKey, number> = {
  portable_pastila: 0.01,
  portable_0_50: 0.04,
  portable_51_150: 0.11,
  portable_151_250: 0.38,
  portable_251_500: 0.80,
  portable_501_750: 0.98,
  portable_751_1000: 1.20,
  portable_1000_plus: 1.38,
};

// greutate estimată per bucată (kg) — la fel ca pe server
export const PORTABLE_WEIGHTS_KG: Record<PortableKey, number> = {
  portable_pastila: 0.010,
  portable_0_50: 0.050,
  portable_51_150: 0.150,
  portable_151_250: 0.250,
  portable_251_500: 0.500,
  portable_501_750: 0.750,
  portable_751_1000: 1.000,
  portable_1000_plus: 1.000,
};

// tarife pe kg (RON/kg) — la fel ca pe server
export const KG_RATES: Record<KgKey, number> = {
  auto_3a: 0.35,
  auto_3b: 1.38,
  auto_3c: 1.38,
  industrial_4a: 0.35,
  industrial_4b: 1.38,
  industrial_4c: 1.38,
};
