import { MigrationInterface, QueryRunner } from 'typeorm';

export class AddExternalOrderNumber1790001000000 implements MigrationInterface {
  name = 'AddExternalOrderNumber1790001000000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      ALTER TABLE "orders"
      ADD COLUMN "external_order_number" character varying
    `);

    await queryRunner.query(`
      UPDATE "orders"
      SET "external_order_number" = 'LEGACY-' || "id"::text
      WHERE "external_order_number" IS NULL
    `);

    await queryRunner.query(`
      ALTER TABLE "orders"
      ADD CONSTRAINT "UQ_orders_external_order_number"
      UNIQUE ("external_order_number")
    `);

    await queryRunner.query(`
      CREATE UNIQUE INDEX "UQ_order_items_order_product"
      ON "order_items" ("orderId", "productId")
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      ALTER TABLE "orders"
      DROP CONSTRAINT "UQ_orders_external_order_number"
    `);
    await queryRunner.query(`
      DROP INDEX "UQ_order_items_order_product"
    `);
    await queryRunner.query(`
      ALTER TABLE "orders"
      DROP COLUMN "external_order_number"
    `);
  }
}
