import { MigrationInterface, QueryRunner } from 'typeorm';

export class CreateTopSellingProductsReport1790002000000
  implements MigrationInterface
{
  name = 'CreateTopSellingProductsReport1790002000000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      CREATE OR REPLACE FUNCTION top_selling_products(
        p_from date,
        p_to date,
        p_limit integer DEFAULT 5
      )
      RETURNS TABLE (
        product_id integer,
        sku character varying,
        name character varying,
        units_sold bigint,
        sales_amount numeric,
        current_stock integer
      )
      LANGUAGE sql
      STABLE
      AS $$
        SELECT
          p.id AS product_id,
          p.sku,
          p.name,
          SUM(oi.quantity)::bigint AS units_sold,
          SUM(oi.quantity * oi.unit_price)::numeric AS sales_amount,
          p.stock AS current_stock
        FROM products p
        INNER JOIN order_items oi ON oi."productId" = p.id
        INNER JOIN orders o ON oi."orderId" = o.id
        WHERE o.date >= p_from
          AND o.date < p_to + INTERVAL '1 day'
          AND UPPER(o.status) NOT IN ('ANULADO', 'CANCELADO')
        GROUP BY p.id, p.sku, p.name, p.stock
        ORDER BY units_sold DESC, sales_amount DESC, p.sku ASC
        LIMIT GREATEST(p_limit, 1)
      $$;
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      DROP FUNCTION IF EXISTS top_selling_products(date, date, integer)
    `);
  }
}