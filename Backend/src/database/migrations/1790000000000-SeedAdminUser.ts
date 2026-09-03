import { MigrationInterface, QueryRunner } from 'typeorm';

export class SeedAdminUser1790000000000 implements MigrationInterface {
  name = 'SeedAdminUser1790000000000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      INSERT INTO "users" ("username", "password_hash", "role")
      VALUES (
        'admin',
        '$2b$10$BvJCeYkm/YROxL0kWL/rBue6T9YXk/tB74sF5Q80Pu56ODTVo57aS',
        'admin'
      )
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      DELETE FROM "users"
      WHERE "username" = 'admin'
    `);
  }
}