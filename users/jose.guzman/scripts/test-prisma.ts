import { PrismaClient } from '@prisma/client';

// Initialize Prisma Client
const prisma = new PrismaClient({
  log: ['query', 'info', 'warn', 'error'],
});

/**
 * Main function to test Prisma Client operations
 */
async function main() {
  try {
    console.log('Starting Prisma test operations...');

    // Step 1: Create a publisher
    console.log('Creating a publisher...');
    const publisher = await prisma.publisher.create({
      data: {
        name: 'test-publisher',
        displayName: 'Test Publisher',
      },
    });
    console.log(`Publisher created: ${JSON.stringify(publisher, null, 2)}`);

    // Step 2: Create an extension linked to the publisher
    console.log('Creating an extension...');
    const extension = await prisma.extension.create({
      data: {
        uniqueName: 'test-publisher.test-extension',
        displayName: 'Test Extension',
        description: 'A test extension for verifying Prisma client',
        publisher: {
          connect: { id: publisher.id },
        },
      },
      include: {
        publisher: true, // Include the publisher data in the response
      },
    });
    console.log(`Extension created: ${JSON.stringify(extension, null, 2)}`);

    // Step 3: Create a version for the extension
    console.log('Creating a version for the extension...');
    const version = await prisma.version.create({
      data: {
        version: '1.0.0',
        extension: {
          connect: { id: extension.id },
        },
        changelog: 'Initial release',
      },
    });
    console.log(`Version created: ${JSON.stringify(version, null, 2)}`);

    // Step 4: Query the extension with its relations
    console.log('Querying the extension with its relations...');
    const fullExtension = await prisma.extension.findUnique({
      where: { id: extension.id },
      include: {
        publisher: true,
        versions: true,
      },
    });
    console.log(`Full extension data: ${JSON.stringify(fullExtension, null, 2)}`);

    console.log('All operations completed successfully!');
  } catch (error) {
    console.error('Error during Prisma operations:', error);
    throw error;
  } finally {
    // Always disconnect from the database
    await prisma.$disconnect();
    console.log('Disconnected from the database');
  }
}

// Execute the main function and handle any uncaught errors
main()
  .catch((error) => {
    console.error('Unhandled error in main function:', error);
    process.exit(1);
  });

import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  try {
    // Create a publisher
    const publisher = await prisma.publisher.create({
      data: {
        name: 'microsoft',  // Unique identifier for the publisher
        displayName: 'Microsoft',  // Display name can have proper casing
      },
    });
    console.log('Created publisher:', publisher);

    // Create a category
    const category = await prisma.category.create({
      data: {
        name: 'Programming Languages',
      },
    });
    console.log('Created category:', category);

    // Create an extension
    const extension = await prisma.extension.create({
      data: {
        displayName: 'Python',
        uniqueName: 'ms-python.python',
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
    const version = await prisma.version.create({
      data: {
        version: '1.0.0',
        extensionId: extension.id,
        changelog: 'Initial release',
        assets: {
          vsix: 'https://marketplace.visualstudio.com/items?itemName=ms-python.python',
        },
        releaseDate: new Date(),
      },
    });
    console.log('Created version:', version);

    // Create a rating for the extension
    const rating = await prisma.rating.create({
      data: {
        rating: 5,
        review: 'Great extension!',
        extensionId: extension.id,
      },
    });
    console.log('Created rating:', rating);

    // Query the extension with all its relations
    const result = await prisma.extension.findUnique({
      where: { id: extension.id },
      include: {
        publisher: true,
        categories: true,
        ratings: true,
        versions: true,
      },
    });

    console.log('Full extension data:', JSON.stringify(result, null, 2));

  } catch (error) {
    console.error('Error:', error);
  } finally {
    await prisma.$disconnect();
  }
}

main();

import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  try {
    // Create a publisher
    const publisher = await prisma.publisher.create({
      data: {
        name: 'Microsoft',
        displayName: 'Microsoft',
      },
    });
    console.log('Created publisher:', publisher);

    // Create a category
    const category = await prisma.category.create({
      data: {
        name: 'Programming Languages',
      },
    });
    console.log('Created category:', category);

    // Create an extension
    const extension = await prisma.extension.create({
      data: {
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

    // Create a version
    const version = await prisma.version.create({
      data: {
        version: '1.0.0',
        extensionId: extension.id,
        changelog: 'Initial release',
        assets: {
          vsix: 'https://marketplace.visualstudio.com/items?itemName=ms-python.python',
        },
      },
    });
    console.log('Created version:', version);

    // Query the extension with all its relations
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
    console.error('Error:', error);
  } finally {
    await prisma.$disconnect();
  }
}

main();

