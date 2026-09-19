import { config as loadDotenv } from 'dotenv';
import { z } from 'zod';

loadDotenv();

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  PORT: z.coerce.number().int().positive().default(3000),

  DATABASE_URL: z.string().min(1, 'DATABASE_URL es requerido'),

  MAX_UPLOAD_MB: z.coerce.number().int().positive().default(10),

  // Carpeta donde el pipeline de Python (DVC) deja sus artefactos reales
  // (`quality_metrics.json` de T-202, etc.). Es configurable porque en
  // Docker la carpeta se monta, no viaja dentro de la imagen; la ruta es
  // relativa a la raíz del repo si no es absoluta.
  PIPELINE_ARTIFACTS_DIR: z.string().min(1).default('data/processed'),

  // Política de la compuerta (`quality.yaml`). La pantalla Settings la edita
  // en disco, así que en Docker se monta con permiso de escritura.
  QUALITY_POLICY_PATH: z.string().min(1).default('quality.yaml'),

  // Imágenes crudas del dataset (DVC). Sirven para mostrar miniaturas de las
  // muestras ofensoras y el hover de la analítica exploratoria.
  RAW_IMAGES_DIR: z.string().min(1).default('data/raw/images'),

  MINIO_ENDPOINT: z.string().min(1),
  MINIO_PORT: z.coerce.number().int().positive(),
  MINIO_USE_SSL: z
    .string()
    .default('false')
    .transform((value) => value === 'true'),
  MINIO_ACCESS_KEY: z.string().min(1),
  MINIO_SECRET_KEY: z.string().min(1),
  MINIO_BUCKET: z.string().min(1),
});

export type Env = z.infer<typeof envSchema>;

function loadEnv(): Env {
  const parsed = envSchema.safeParse(process.env);
  if (!parsed.success) {
    console.error('Variables de entorno inválidas:', parsed.error.flatten().fieldErrors);
    throw new Error('Configuración de entorno inválida. Revisa tu archivo .env');
  }
  return parsed.data;
}

export const env = loadEnv();
