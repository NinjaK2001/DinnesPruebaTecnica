import {
  BadRequestException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { DataSource } from 'typeorm';

import { Order } from './entities/order.entity';
import { OrderItem } from './entities/order-item.entity';
import { Product } from '../products/entities/product.entity';
import { CreateOrderDto } from './dto/create-order.dto';

@Injectable()
export class OrdersService {
  constructor(private readonly dataSource: DataSource) {}

  async findTopProducts(from: string, to: string) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(from ?? '') || !/^\d{4}-\d{2}-\d{2}$/.test(to ?? '')) {
      throw new BadRequestException(
        'from y to deben tener formato YYYY-MM-DD',
      );
    }

    if (from > to) {
      throw new BadRequestException(
        'from no puede ser posterior a to',
      );
    }

    return this.dataSource.query(
      'SELECT * FROM top_selling_products($1::date, $2::date, $3)',
      [from, to, 5],
    );
  }

  async create(createOrderDto: CreateOrderDto): Promise<Order> {
    return this.dataSource.transaction(async (manager) => {
      const order = manager.create(Order, {
        customer: createOrderDto.customer,
        date: new Date(),
        status: 'COMPLETED',
      });

      const savedOrder = await manager.save(Order, order);

      for (const item of createOrderDto.items) {
        const product = await manager.findOne(Product, {
          where: { id: item.productId },
          lock: { mode: 'pessimistic_write' },
        });

        if (!product) {
          throw new NotFoundException(
            `Product with id ${item.productId} not found`,
          );
        }

        if (product.stock < item.quantity) {
          throw new BadRequestException(
            `Insufficient stock for product ${product.name}`,
          );
        }

        product.stock -= item.quantity;
        await manager.save(Product, product);

        const orderItem = manager.create(OrderItem, {
          order: savedOrder,
          product,
          quantity: item.quantity,
          unit_price: product.price,
        });

        await manager.save(OrderItem, orderItem);
      }

      return savedOrder;
    });
  }
}