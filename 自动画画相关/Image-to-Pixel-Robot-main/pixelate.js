#!/usr/bin/env node

/**
 * pixelate.js - Dead simple batch pixelation script
 * 
 * Usage: node pixelate.js --in <dir> --out <dir> --size <pixels>
 * Example: node pixelate.js --in ./images --out ./output --size 128
 */

const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

// Parse command line args - no fancy libraries needed
function parseArgs() {
    const args = process.argv.slice(2);
    const options = {
        in: null,
        out: null,
        size: 128
    };
    
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--in' && args[i + 1]) {
            options.in = args[i + 1];
            i++;
        } else if (args[i] === '--out' && args[i + 1]) {
            options.out = args[i + 1];
            i++;
        } else if (args[i] === '--size' && args[i + 1]) {
            options.size = parseInt(args[i + 1]);
            i++;
        }
    }
    
    return options;
}

// Check if file is an image
function isImageFile(filename) {
    const ext = path.extname(filename).toLowerCase();
    return ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'].includes(ext);
}

// Pixelate a single image
async function pixelateImage(inputPath, outputPath, pixelSize) {
    try {
        // Get original image metadata
        const metadata = await sharp(inputPath).metadata();
        const originalWidth = metadata.width;
        const originalHeight = metadata.height;
        
        // Calculate pixel dimensions maintaining aspect ratio
        const aspectRatio = originalHeight / originalWidth;
        const pixelWidth = pixelSize;
        const pixelHeight = Math.round(pixelSize * aspectRatio);
        
        // Process: resize down to pixel size, then back up to original
        await sharp(inputPath)
            // Step 1: Resize down to pixel dimensions
            .resize(pixelWidth, pixelHeight, {
                kernel: sharp.kernel.nearest,  // Use nearest neighbor for crisp pixels
                fit: 'fill'
            })
            // Step 2: Resize back up to original dimensions
            .resize(originalWidth, originalHeight, {
                kernel: sharp.kernel.nearest,  // Maintain pixelated look
                fit: 'fill'
            })
            // Save the result
            .toFile(outputPath);
            
        return true;
    } catch (error) {
        console.error(`Error processing ${inputPath}:`, error.message);
        return false;
    }
}

// Main function
async function main() {
    const options = parseArgs();
    
    // Validate arguments
    if (!options.in || !options.out) {
        console.error('Usage: node pixelate.js --in <input_dir> --out <output_dir> --size <pixel_width>');
        console.error('Example: node pixelate.js --in ./images --out ./output --size 128');
        process.exit(1);
    }
    
    // Check if input directory exists
    if (!fs.existsSync(options.in)) {
        console.error(`Input directory does not exist: ${options.in}`);
        process.exit(1);
    }
    
    // Create output directory if it doesn't exist
    if (!fs.existsSync(options.out)) {
        fs.mkdirSync(options.out, { recursive: true });
        console.log(`Created output directory: ${options.out}`);
    }
    
    // Get all image files in input directory
    const files = fs.readdirSync(options.in).filter(isImageFile);
    
    if (files.length === 0) {
        console.error('No image files found in input directory');
        process.exit(1);
    }
    
    console.log(`Found ${files.length} images to process`);
    console.log(`Pixel size: ${options.size}px wide`);
    console.log('Processing...\n');
    
    let successful = 0;
    let failed = 0;
    
    // Process each image
    for (const file of files) {
        const inputPath = path.join(options.in, file);
        const outputPath = path.join(options.out, `pixelated_${file}`);
        
        process.stdout.write(`Processing ${file}... `);
        
        const success = await pixelateImage(inputPath, outputPath, options.size);
        
        if (success) {
            console.log('✓');
            successful++;
        } else {
            console.log('✗');
            failed++;
        }
    }
    
    // Summary
    console.log('\n--- Complete ---');
    console.log(`Successful: ${successful}`);
    console.log(`Failed: ${failed}`);
    console.log(`Output directory: ${options.out}`);
}

// Run it
main().catch(console.error);