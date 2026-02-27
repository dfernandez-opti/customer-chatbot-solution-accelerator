// Copia el logo OPTI desde src/images al public del frontend
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(__dirname, '..', 'images', 'descarga-removebg-preview.png');
const dest = path.join(__dirname, 'public', 'opti-logo.png');

if (fs.existsSync(src)) {
  fs.copyFileSync(src, dest);
  console.log('Logo copiado a public/opti-logo.png');
} else {
  console.warn('Logo no encontrado en', src);
}
