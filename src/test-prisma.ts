import { PrismaClient } from '@prisma/client';
import { randomUUID } from 'crypto';

const prisma = new PrismaClient({
  log: ['query', 'info', 'warn', 'error'],
});

async function main() {
  console.log('Starting test script...');
  
  try {
    // Create a publisher
    console.log('Creating publisher...');
    const publisher = await prisma.publisher.create({
      data: {
        id: randomUUID(),
        name: 'microsoft',
        displayName: 'Microsoft',
      },
    });
    console.log('Created publisher:', publisher);

    // Create a category
    console.log('Creating category...');
    const category = await prisma.category.create({
      data: {
        id: randomUUID(),
        name: 'Programming Languages',
      },
    });
    console.log('Created category:', category);

    // Create an extension
    console.log('Creating extension...');
    const extension = await prisma.extension.create({
      data: {
        id: randomUUID(),
        uniqueName: 'ms-python.python',
        displayName: 'Python',
        description: 'Python language support for Visual Studio Code',
        publisherId: publisher.id,
        categories: {
          connect: [{ id: category.id }],
        },
        icon: 'https://raw.githubusercontent.com/microsoft/vscode-python/main/icon.png',
        repository: 'https://github.com/microsoft/vscode-python',
      },
    });
    console.log('Created extension:', extension);

    // Create a version for the extension
    console.log('Creating version...');
    const extensionVersion = await prisma.version.create({
      data: {
        id: randomUUID(),
        version: '1.0.0',
        extensionId: extension.id,
        changelog: 'Initial release',
        assets: {
          vsix: 'https://marketplace.visualstudio.com/items?itemName=ms-python.python',
        },
        // releaseDate is set automatically by default
      },
    });
    console.log('Created version:', extensionVersion);

    // Create a rating for the extension
    console.log('Creating rating...');
    const extensionRating = await prisma.rating.create({
      data: {
        id: randomUUID(),
        rating: 5,
        review: 'Great extension!',
        extensionId: extension.id,
      },
    });
    console.log('Created rating:', extensionRating);

    // Query the extension with all its relations
    console.log('Querying full extension data...');
    const result = await prisma.extension.findUnique({
      where: { id: extension.id },
      include: {
        publisher: true,
        categories: true,
        versions: true,
        ratings: true,
      },
    });

    console.log('Full extension data:', JSON.stringify(result, null, 2));
  } catch (error) {
    console.error('Error occurred:', error);
    if (error instanceof Error) {
      console.error('Error stack:', error.stack);
    }
    process.exit(1);
  } finally {
    console.log('Disconnecting Prisma client...');
    await prisma.$disconnect();
  }
}

console.log('Script loaded, running main()...');
main().catch(error => {
  console.error('Unhandled error:', error);
  process.exit(1);
});
