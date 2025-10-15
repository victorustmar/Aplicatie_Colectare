// src/lib/batteries.ts
// Etichete și ordinea rândurilor pentru tabelul din UI (în română).

export const BATTERY_LABELS: Record<string, string> = {
  // Portabile – cat. 1
  "1a": "Alcaline",
  "1b": "Litiu",
  "1c": "Zinc carbon",
  "1d": "Zinc aer",
  "1e": "Oxid de mercur (HgO)",
  "1f": "Oxid de argint (Ag₂O)",
  "1g": "Ansamblu de baterii",
  "1h": "Altele",

  // Portabile – cat. 2
  "2a": "Nichel Cadmiu (NiCd)",
  "2b": "Plumb",
  "2c": "Nichel metal hidrură (NiMH)",
  "2d": "Litiu ion",
  "2e": "Litiu polimer",
  "2f": "Altele",

  // Auto – cat. 3
  "3a": "Plumb acid",
  "3b": "Nichel cadmiu (NiCd)",
  "3c": "Altele",

  // Industriale – cat. 4
  "4a": "Plumb acid",
  "4b": "Nichel cadmiu (NiCd)",
  "4c": "Altele",
};

export const BATTERY_SECTIONS: { id: string; title: string; keys: string[] }[] = [
  {
    id: "portable12",
    title: "Baterii portabile (categoriile 1 și 2)",
    keys: ["1a","1b","1c","1d","1e","1f","1g","1h","2a","2b","2c","2d","2e","2f"],
  },
  { id: "auto3", title: "Baterii auto (categoria 3)", keys: ["3a","3b","3c"] },
  { id: "industrial4", title: "Baterii industriale (categoria 4)", keys: ["4a","4b","4c"] },
];

export const BATTERY_KEYS_ORDER = BATTERY_SECTIONS.flatMap(s => s.keys);

// Helper pentru stare inițială a formularului
export const emptyBatteryLine = { pcs: 0, weight_kg: 0, price_ron: 0 };
