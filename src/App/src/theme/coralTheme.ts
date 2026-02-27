import { 
  Theme,
  createLightTheme,
  createDarkTheme,
  BrandVariants,
  themeToTokensObject
} from '@fluentui/react-components';

// Brand colors from OPTI logo - vibrant orange, blue-grey, and accent grey
const optiBrand: BrandVariants = {
  10: "#1a0d08",
  20: "#2d150c",
  30: "#4a1f10",
  40: "#672914",
  50: "#843318",
  60: "#a13d1c",
  70: "#be4720",
  80: "#db5124",
  90: "#E85D2C",
  100: "#E85D2C",
  110: "#EB6F42",
  120: "#EE8158",
  130: "#F1936E",
  140: "#F4A584",
  150: "#F7B79A",
  160: "#FAC9B0"
};

// Create light theme
export const coralLightTheme: Theme = {
  ...createLightTheme(optiBrand),
};

// Create dark theme with OPTI branding
export const coralDarkTheme: Theme = {
  ...createDarkTheme(optiBrand),
  // Override specific colors for OPTI dark theme
  colorNeutralBackground1: "#1a1a1a",
  colorNeutralBackground2: "#262626",
  colorNeutralBackground3: "#333333",
  colorNeutralForeground1: "#ffffff",
  colorNeutralForeground2: "#e6e6e6",
  colorNeutralForeground3: "#cccccc",
  colorBrandBackground: "#E85D2C",
  colorBrandForeground1: "#ffffff",
  colorBrandForeground2: "#e6e6e6",
};

// Theme tokens for CSS custom properties
export const lightThemeTokens = themeToTokensObject(coralLightTheme);
export const darkThemeTokens = themeToTokensObject(coralDarkTheme);

// CSS custom properties for easy theme switching
export const createThemeStyles = (theme: Theme) => {
  const tokens = themeToTokensObject(theme);
  return Object.entries(tokens).reduce((acc, [key, value]) => {
    acc[`--${key}`] = value;
    return acc;
  }, {} as Record<string, string>);
};
