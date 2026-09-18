import { drizzle } from 'drizzle-orm/mysql2';
import mysql from 'mysql2/promise';
import * as schema from './schema';

/**
 * Base de datos exclusiva para los tests de integración de `db.test.ts`.
 *
 * Incidente real que motiva este archivo: `db.test.ts` hace `DROP TABLE` +
 * recrea el esquema en cada corrida — diseño correcto contra una MariaDB
 * descartable (como en CI), pero corriendo por error contra la misma
 * `DATABASE_URL` de desarrollo, un `npm test` local borró 100 imágenes y
 * 308 anotaciones reales ya guardadas por un usuario.
 *
 * Esta base se deriva de `DATABASE_URL` agregando el sufijo `_test` al
 * nombre — nunca es la base real — y se crea sola (`ensureTestDatabaseExists`)
 * si todavía no existe, para que nadie tenga que hacerlo a mano.
 */

function buildTestDatabaseUrl(databaseUrl: string): { url: string; dbName: string } {
  const parsed = new URL(databaseUrl);
  const dbName = `${parsed.pathname.replace(/^\//, '')}_test`;
  parsed.pathname = `/${dbName}`;
  return { url: parsed.toString(), dbName };
}

const { url: testDatabaseUrl, dbName: testDbName } = buildTestDatabaseUrl(
  process.env.DATABASE_URL ?? 'mysql://annotation_user:changeme@localhost:3306/annotation_portal',
);

// Crea la base de test (si falta) y le otorga permisos al usuario normal de
// la app — usa el usuario root de docker-compose (DB_ROOT_PASSWORD), que
// nunca se necesita para nada más que esto. No usa `env.ts`/Zod a propósito:
// es infraestructura solo de tests, no parte del contrato de runtime de la app.
export async function ensureTestDatabaseExists(): Promise<void> {
  const root = await mysql.createConnection({
    host: process.env.DB_HOST ?? 'localhost',
    port: Number(process.env.DB_PORT ?? 3306),
    user: 'root',
    password: process.env.DB_ROOT_PASSWORD ?? 'changeme_root',
  });
  try {
    const dbUser = process.env.DB_USER ?? 'annotation_user';
    await root.query(`CREATE DATABASE IF NOT EXISTS \`${testDbName}\``);
    await root.query(`GRANT ALL PRIVILEGES ON \`${testDbName}\`.* TO '${dbUser}'@'%'`);
    await root.query('FLUSH PRIVILEGES');
  } finally {
    await root.end();
  }
}

export const testPool = mysql.createPool({ uri: testDatabaseUrl, connectionLimit: 5 });
export const testDb = drizzle(testPool, { schema, mode: 'default' });
