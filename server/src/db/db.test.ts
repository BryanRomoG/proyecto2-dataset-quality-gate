import { sql } from 'drizzle-orm';
import { migrate } from 'drizzle-orm/mysql2/migrator';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { annotations, categories, images } from './schema';
import { seed } from './seed';
import { testDb as db, ensureTestDatabaseExists, testPool as pool } from './test-client';

// Cuántas filas "de muestra" puede haber sin que sea trabajo real: los 3
// seed-assets. Por encima de eso, casi seguro es anotación real de alguien
// (visto en producción: corrimos `npm test` contra `DATABASE_URL` en vez de
// la base de tests, y borró 100 imágenes/308 anotaciones reales ya
// guardadas). Ahora este archivo corre contra su propia base aislada
// (test-client.ts) — esta guarda queda como defensa adicional, por si algo
// llega a apuntar mal la conexión otra vez.
const MAX_SAFE_ROWS_BEFORE_DROP = 10;

async function currentImageCount(): Promise<number> {
  try {
    const [rows] = await pool.query('SELECT COUNT(*) as count FROM images');
    const [{ count }] = rows as [{ count: number }];
    return Number(count);
  } catch (error) {
    // La tabla todavía no existe (primera corrida contra una BD nueva) —
    // no hay nada real que proteger.
    if ((error as { code?: string }).code === 'ER_NO_SUCH_TABLE') {
      return 0;
    }
    throw error;
  }
}

async function dropAllTables(): Promise<void> {
  const count = await currentImageCount();
  if (count > MAX_SAFE_ROWS_BEFORE_DROP) {
    throw new Error(
      `db.test.ts iba a borrar la tabla 'images', que tiene ${count} filas — mucho más que los 3 de muestra esperados. Esto parece trabajo real de anotación, no una base de datos de prueba vacía. Corre este test solo contra una MariaDB descartable (como en CI), nunca contra tu base de desarrollo local con anotaciones reales.`,
    );
  }

  await db.execute(sql`SET FOREIGN_KEY_CHECKS = 0`);
  await db.execute(sql`DROP TABLE IF EXISTS annotations`);
  await db.execute(sql`DROP TABLE IF EXISTS images`);
  await db.execute(sql`DROP TABLE IF EXISTS categories`);
  await db.execute(sql`DROP TABLE IF EXISTS __drizzle_migrations`);
  await db.execute(sql`SET FOREIGN_KEY_CHECKS = 1`);
}

describe('migraciones sobre una base de datos vacía', () => {
  beforeAll(async () => {
    await ensureTestDatabaseExists();
    await dropAllTables();
  });

  it('crea todas las tablas del esquema sin intervención manual', async () => {
    await migrate(db, { migrationsFolder: './drizzle' });

    await expect(db.select().from(categories)).resolves.toEqual([]);
    await expect(db.select().from(images)).resolves.toEqual([]);
    await expect(db.select().from(annotations)).resolves.toEqual([]);
  });
});

describe('seeder idempotente', () => {
  it('inserta las categorías e imágenes de ejemplo', async () => {
    await seed(db);

    const categoryRows = await db.select().from(categories);
    const imageRows = await db.select().from(images);

    expect(categoryRows.length).toBeGreaterThan(0);
    expect(imageRows.length).toBeGreaterThan(0);
  });

  it('no duplica registros al ejecutarse más de una vez', async () => {
    const categoriesBefore = await db.select().from(categories);
    const imagesBefore = await db.select().from(images);

    await seed(db);
    await seed(db);

    const categoriesAfter = await db.select().from(categories);
    const imagesAfter = await db.select().from(images);

    expect(categoriesAfter).toHaveLength(categoriesBefore.length);
    expect(imagesAfter).toHaveLength(imagesBefore.length);
  });
});

afterAll(async () => {
  await pool.end();
});
