import { Injectable,
    NotFoundException,
 } from '@nestjs/common';

import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';

import { Product } from './entities/product.entity';
import { CreateProductDto } from './dto/create-product.dto';
import { UpdateProductDto } from './dto/update-product.dto';

@Injectable()
export class ProductsService {
    constructor(
        @InjectRepository(Product)
        private readonly productsRepository: Repository<Product>
    ){}

    create(createProductDto: CreateProductDto): Promise<Product> {
        const product = this.productsRepository.create(createProductDto);
        return this.productsRepository.save(product);
    }

     findAll() {
        return this.productsRepository.find();
    }

    async findById(id: number) {
        const product = await this.productsRepository.findOneBy({ id });

        if (!product) {
        throw new NotFoundException(
            `Product with id ${id} not found`,
        );
        }
        return product;
    }

    async update(id: number, updateProductDto: UpdateProductDto) {
        const product = await this.findById(id);

        Object.assign(product, updateProductDto);

        return this.productsRepository.save(product);
    }

    async remove(id: number) {
        const product = await this.findById(id);

        await this.productsRepository.remove(product);

        return {
        message: 'Product deleted successfully',
        };
    }
}