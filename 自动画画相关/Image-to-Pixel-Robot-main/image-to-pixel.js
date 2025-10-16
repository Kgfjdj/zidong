/**
 * image-to-pixel.js - Core pixelation and dithering engine for training data generation
 * 
 * PURPOSE:
 * This module implements the core algorithms for converting high-resolution images
 * into pixel art suitable for training machine learning models. It provides various
 * dithering methods and palette quantization techniques.
 * 
 * ARCHITECTURE:
 * - Supports multiple input formats (Canvas, Image, ImageData, URLs)
 * - Processes images through a pipeline: Load -> Resize -> Dither -> Quantize -> Export
 * - Integrates with p5.js and Q5.js for creative coding workflows
 * 
 * CONNECTIONS:
 * - Called by index.html's applyPixelation() function
 * - Fetches palettes from Lospec API when palette names are provided
 * - Returns canvas elements for display and export
 * 
 * TRAINING DATA CONSIDERATIONS:
 * - Maintains consistent pixel grid alignment
 * - Preserves color relationships through careful quantization
 * - Supports batch processing with identical parameters
 */

/**
 * Configuration constants for pixelation algorithms.
 * These values control the behavior of various image processing operations.
 */
const PixelationConstants = {
    /** Default pixel width when none specified */
    DEFAULT_PIXEL_WIDTH: 128,
    /** Minimum pixel width to prevent degenerate cases */
    MIN_PIXEL_WIDTH: 2,
    /** Maximum pixel width to prevent memory issues */
    MAX_PIXEL_WIDTH: 4096,
    /** Default dithering strength percentage */
    DEFAULT_DITHER_STRENGTH: 10,
    /** Cache timeout for Lospec palette fetches in milliseconds */
    PALETTE_CACHE_TIMEOUT: 3600000, // 1 hour
};

/**
 * Dithering algorithm coefficients.
 * These control error diffusion in various dithering methods.
 */
const DitheringCoefficients = {
    /** Floyd-Steinberg error diffusion coefficients */
    FLOYD_STEINBERG: {
        RIGHT: 7 / 16,
        BOTTOM_LEFT: 3 / 16,
        BOTTOM: 5 / 16,
        BOTTOM_RIGHT: 1 / 16
    },
    /** Atkinson dithering uses 1/8 for all directions */
    ATKINSON: {
        COEFFICIENT: 1 / 8
    },
    /** Threshold adjustment for ordered dithering */
    ORDERED_THRESHOLD_CENTER: 127.5
};

/**
 * Pixelate and dither an image for training data generation.
 * 
 * This is the main entry point for the pixelation pipeline. It coordinates
 * all processing steps and ensures consistent output suitable for ML training.
 * 
 * PROCESS FLOW:
 * 1. Load image from various input formats
 * 2. Fetch color palette if specified
 * 3. Resize to target pixel dimensions
 * 4. Apply dithering algorithm if requested
 * 5. Quantize colors to palette
 * 6. Optionally scale back to original resolution
 * 
 * @param {Object} options - Configuration options for pixelation
 * @param {HTMLCanvasElement|HTMLImageElement|p5.Renderer|p5.Image|Q5.Image|ImageData|string} options.image - 
 *        Input image in various formats. Can be a canvas, image element, p5/Q5 object, or URL string
 * @param {number} options.width - Target width in pixels for the pixelated output
 * @param {string} [options.dither='none'] - Dithering algorithm to apply:
 *        'none' - No dithering, direct color quantization
 *        'floyd-steinberg' - Classic error diffusion, good for photos
 *        'atkinson' - Lower contrast error diffusion, good for graphics
 *        'ordered' - 8x8 Bayer matrix, creates consistent patterns
 *        '2x2 bayer' - Small pattern, subtle dithering
 *        '4x4 bayer' - Medium pattern, balanced dithering
 *        'clustered 4x4' - Clustered dot pattern, good for printing
 * @param {number} [options.strength=0] - Dithering intensity (0-100). 
 *        0 = no dithering, 100 = maximum error diffusion
 * @param {string|Array} [options.palette=null] - Color palette for quantization:
 *        String: Lospec palette name (e.g., 'pico-8', 'endesga-32')
 *        Array: Custom palette as hex colors ['#FF0000', '#00FF00', ...]
 *        null: No palette quantization, preserve original colors
 * @param {string} [options.resolution='original'] - Output resolution:
 *        'pixel' - Output at actual pixel size (e.g., 32x32)
 *        'original' - Scale back to original image dimensions
 * @returns {Promise<HTMLCanvasElement|p5.Image|Q5.Image>} Canvas with pixelated result
 * @throws {Error} If required parameters are missing or invalid
 */
async function pixelate(options) {
    const {
        image,
        width,
        dither = 'none',
        strength = 0,
        palette = null,
        resolution = 'original',
    } = options;

    // Validate required parameters
    if (!image) {
        throw new Error('Image parameter is required for pixelation.');
    }
    if (!width || width < PixelationConstants.MIN_PIXEL_WIDTH) {
        throw new Error(`Width must be at least ${PixelationConstants.MIN_PIXEL_WIDTH} pixels.`);
    }
    if (width > PixelationConstants.MAX_PIXEL_WIDTH) {
        throw new Error(`Width cannot exceed ${PixelationConstants.MAX_PIXEL_WIDTH} pixels.`);
    }
    // Check for p5 and Q5 availability
    const isP5Available = typeof p5 !== 'undefined';
    const isQ5Available = typeof Q5 !== 'undefined';

    // Load the image with support for multiple input formats
    const originalImageObject = await loadOriginalImage(image);

    let paletteColors = null;

    // Fetch palette if provided
    if (palette) {
        if (Array.isArray(palette)) {
            paletteColors = palette.map(hexToRgb);
        } else if (typeof palette === 'string') {
            paletteColors = await fetchPalette(palette);
        }
    }

    // Calculate pixel dimensions
    const aspectRatio = originalImageObject.height / originalImageObject.width;
    const pixelsWide = width;
    const pixelsHigh = Math.round(pixelsWide * aspectRatio);

    let offscreenCanvas, offscreenCtx;

    if (originalImageObject instanceof HTMLCanvasElement) {
        // Check if the canvas needs to be resized
        if (originalImageObject.width !== pixelsWide || originalImageObject.height !== pixelsHigh) {
            // Create an offscreen canvas with the new size
            offscreenCanvas = document.createElement('canvas');
            offscreenCanvas.width = pixelsWide;
            offscreenCanvas.height = pixelsHigh;
            offscreenCtx = offscreenCanvas.getContext('2d');

            // Draw the original canvas onto the resized offscreen canvas
            offscreenCtx.drawImage(originalImageObject, 0, 0, pixelsWide, pixelsHigh);
        } else {
            // No resizing needed, reuse the original canvas
            offscreenCanvas = originalImageObject;
            offscreenCtx = offscreenCanvas.getContext('2d');
        }
    } else {
        // Handle image or other input types by creating an offscreen canvas
        offscreenCanvas = document.createElement('canvas');
        offscreenCanvas.width = pixelsWide;
        offscreenCanvas.height = pixelsHigh;
        offscreenCtx = offscreenCanvas.getContext('2d');

        // Draw the original image onto the offscreen canvas
        offscreenCtx.drawImage(
            originalImageObject,
            0, 0, originalImageObject.width, originalImageObject.height,
            0, 0, pixelsWide, pixelsHigh
        );
    }

    // Get image data for manipulation
    let pixelatedData = offscreenCtx.getImageData(0, 0, pixelsWide, pixelsHigh);

    /**
     * Apply dithering and color palette quantization.
     * 
     * This section implements the core visual transformation that creates
     * the pixel art aesthetic. The choice of dithering algorithm and palette
     * significantly affects the training data characteristics.
     * 
     * DITHERING ALGORITHMS:
     * - Floyd-Steinberg: Distributes quantization error to neighboring pixels
     * - Atkinson: Similar to Floyd-Steinberg but propagates less error
     * - Ordered: Uses a fixed pattern matrix for consistent results
     * - Bayer: Variants of ordered dithering with different matrix sizes
     * 
     * The strength parameter controls how much the dithering affects the image.
     * For training data, consistent strength across batches is crucial.
     */
    const ditheringStrength = strength / 100; // Normalize strength to 0-1 range
    if (paletteColors && dither.toLowerCase() !== 'none') {
        if (dither.toLowerCase() === 'floyd-steinberg') {
            pixelatedData = floydSteinbergDithering(pixelatedData, pixelsWide, pixelsHigh, ditheringStrength, paletteColors);
        } else if (dither.toLowerCase() === 'ordered') {
            const bayerMatrix = getBayerMatrix('8x8');
            pixelatedData = orderedDithering(pixelatedData, pixelsWide, pixelsHigh, ditheringStrength, paletteColors, bayerMatrix);
        } else if (dither.toLowerCase() === '4x4 bayer') {
            const bayerMatrix = getBayerMatrix('4x4');
            pixelatedData = orderedDithering(pixelatedData, pixelsWide, pixelsHigh, ditheringStrength, paletteColors, bayerMatrix);
        } else if (dither.toLowerCase() === '2x2 bayer') {
            const bayerMatrix = getBayerMatrix('2x2');
            pixelatedData = orderedDithering(pixelatedData, pixelsWide, pixelsHigh, ditheringStrength, paletteColors, bayerMatrix);
        } else if (dither.toLowerCase() === 'clustered 4x4') {
            const clusteredMatrix = getBayerMatrix('clustered 4x4');
            pixelatedData = orderedDithering(pixelatedData, pixelsWide, pixelsHigh, ditheringStrength, paletteColors, clusteredMatrix);
        } else if (dither.toLowerCase() === 'atkinson') {
            pixelatedData = atkinsonDithering(pixelatedData, pixelsWide, pixelsHigh, ditheringStrength, paletteColors);
        } else {
            throw new Error(`Unknown dithering method: ${dither}`);
        }
    } else if (paletteColors) {
        applyPalette(pixelatedData, paletteColors);
    }

    // Put processed image data back onto the offscreen canvas
    offscreenCtx.putImageData(pixelatedData, 0, 0);

    // ⭐ 在这里提取像素数据
    // const pixelData = 344;

    // return 0;
    const pixelData = extractPixelData(offscreenCanvas);
    offscreenCanvas.pixelData = pixelData; // 将数据附加到canvas对象上

    // If resolution is 'original', scale the image back to its original size
    if (resolution === 'original' && offscreenCanvas.width !== originalImageObject.width) {
        const finalCanvas = document.createElement('canvas');
        finalCanvas.width = originalImageObject.width;
        finalCanvas.height = originalImageObject.height;
        const finalCtx = finalCanvas.getContext('2d');
        finalCtx.imageSmoothingEnabled = false;
        finalCtx.drawImage(offscreenCanvas, 0, 0, offscreenCanvas.width, offscreenCanvas.height, 0, 0, finalCanvas.width, finalCanvas.height);

        // ⭐ 将 pixelData 添加到 finalCanvas
        finalCanvas.pixelData = pixelData;

        // Convert the final canvas to a p5.Image or Q5.Image if necessary
        if (isP5Available) {
            const p5Img = canvasToP5Image(finalCanvas);
            p5Img.pixelData = pixelData; // ⭐ 也添加到 p5.Image
            return p5Img;
        } else if (isQ5Available) {
            const q5Img = canvasToQ5Image(finalCanvas);
            q5Img.pixelData = pixelData; // ⭐ 也添加到 Q5.Image
            return q5Img;
        }

        return finalCanvas;
    }

    // ⭐ 将 pixelData 添加到 offscreenCanvas
    offscreenCanvas.pixelData = pixelData;

    // Return the canvas
    if (isP5Available) {
        const p5Img = canvasToP5Image(offscreenCanvas);
        p5Img.pixelData = pixelData; // ⭐ 也添加到 p5.Image
        return p5Img;
    } else if (isQ5Available) {
        const q5Img = canvasToQ5Image(offscreenCanvas);
        q5Img.pixelData = pixelData; // ⭐ 也添加到 Q5.Image
        return q5Img;
    }

    return offscreenCanvas;
}

// 提取像素数据
function extractPixelData(canvas) {
    const ctx = canvas.getContext('2d');
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const pixels = [];

    for (let y = 0; y < canvas.height; y++) {
        const row = [];
        for (let x = 0; x < canvas.width; x++) {
            const index = (y * canvas.width + x) * 4;
            const r = imageData.data[index];
            const g = imageData.data[index + 1];
            const b = imageData.data[index + 2];
            const hex = `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
            row.push(hex);
        }
        pixels.push(row);
    }

    return {
        width: canvas.width,
        height: canvas.height,
        pixels: pixels
    };
}


/**
 * Retrieve the Bayer matrix for ordered dithering patterns.
 * 
 * Bayer matrices create predictable dithering patterns that are useful
 * for training data because they produce consistent, reproducible results.
 * Each matrix size creates different pattern characteristics:
 * 
 * - 2x2: Very subtle, minimal pattern visibility
 * - 4x4: Balanced between subtlety and effectiveness
 * - 8x8: More complex patterns, better tonal range
 * - Clustered 4x4: Groups pixels for dot-pattern effects
 * 
 * These matrices are normalized to work with the threshold calculation
 * in the ordered dithering algorithm.
 * 
 * @param {string} type - The Bayer matrix type to retrieve:
 *        '2x2' - Minimal 2x2 pattern
 *        '4x4' - Standard 4x4 Bayer matrix
 *        '8x8' - Large 8x8 matrix for smooth gradients
 *        'clustered 4x4' - Clustered dot pattern
 * @returns {Array<Array<number>>} The selected Bayer matrix
 * @throws {Error} If an invalid matrix type is specified
 */
function getBayerMatrix(type) {
    switch (type) {
        case '2x2':
            return [
                [0, 2],
                [3, 1]
            ];
        case '4x4':
            return [
                [0, 8, 2, 10],
                [12, 4, 14, 6],
                [3, 11, 1, 9],
                [15, 7, 13, 5]
            ];
        case '8x8':
            return [
                [0, 48, 12, 60, 3, 51, 15, 63],
                [32, 16, 44, 28, 35, 19, 47, 31],
                [8, 56, 4, 52, 11, 59, 7, 55],
                [40, 24, 36, 20, 43, 27, 39, 23],
                [2, 50, 14, 62, 1, 49, 13, 61],
                [34, 18, 46, 30, 33, 17, 45, 29],
                [10, 58, 6, 54, 9, 57, 5, 53],
                [42, 26, 38, 22, 41, 25, 37, 21]
            ];
        case 'clustered 4x4':
            return [
                [7, 13, 11, 4],
                [12, 16, 14, 8],
                [10, 15, 6, 2],
                [5, 9, 3, 1]
            ];
        default:
            throw new Error(`Invalid Bayer matrix type: ${type}`);
    }
}

/**
 * Convert an HTMLCanvasElement to a p5.Image for p5.js integration.
 * 
 * This function enables seamless integration with p5.js creative coding
 * workflows, allowing the pixelated output to be used in p5.js sketches
 * for further processing or artistic applications.
 * 
 * @param {HTMLCanvasElement} canvas - The canvas containing pixelated image
 * @returns {p5.Image|HTMLCanvasElement} p5.Image if p5.js is available, otherwise original canvas
 */
function canvasToP5Image(canvas) {
    if (typeof p5 !== 'undefined') {
        const tempImage = createImage(canvas.width, canvas.height);
        tempImage.drawingContext.drawImage(canvas, 0, 0, canvas.width, canvas.height);
        return tempImage;
    }
    return canvas;
}

/**
 * Convert an HTMLCanvasElement to a Q5.Image for Q5.js integration.
 * 
 * Q5.js is a lightweight alternative to p5.js. This function provides
 * compatibility for projects using Q5.js instead of p5.js.
 * 
 * @param {HTMLCanvasElement} canvas - The canvas containing pixelated image
 * @returns {Q5.Image|HTMLCanvasElement} Q5.Image if Q5.js is available, otherwise original canvas
 */
function canvasToQ5Image(canvas) {
    if (typeof Q5 !== 'undefined' && typeof Q5.Image !== 'undefined') {
        const tempImage = new Q5.Image(canvas.width, canvas.height);
        tempImage.ctx.drawImage(canvas, 0, 0, canvas.width, canvas.height);
        return tempImage;
    }
    return canvas;
}
/**
 * Convert a p5.Graphics object to a standard HTMLCanvasElement.
 * @param {p5.Graphics} p5Graphics - The p5.Graphics object.
 * @returns {Promise<HTMLCanvasElement>} - A promise that resolves to an HTMLCanvasElement.
 */
function convertP5GraphicsToCanvas(p5Graphics) {
    return new Promise((resolve) => {
        const canvasElement = document.createElement('canvas');
        canvasElement.width = p5Graphics.width;
        canvasElement.height = p5Graphics.height;

        const ctx = canvasElement.getContext('2d');
        ctx.drawImage(p5Graphics.elt, 0, 0);

        resolve(canvasElement);
    });
}
/**
 * Load the original image from various input formats.
 * 
 * This function provides a unified interface for loading images from
 * multiple sources, making the library flexible for different workflows.
 * It's essential for batch processing training data from various sources.
 * 
 * SUPPORTED FORMATS:
 * - HTMLImageElement: Direct image elements from the DOM
 * - HTMLCanvasElement: Existing canvas with rendered content
 * - ImageData: Raw pixel data from canvas operations
 * - p5.Graphics/p5.Renderer: p5.js drawing surfaces
 * - Q5.Image/Q5.Graphics: Q5.js image objects
 * - OffscreenCanvas: Web Worker compatible canvases
 * - String URLs: Remote or data URLs for loading images
 * 
 * The function normalizes all inputs to either HTMLImageElement or
 * HTMLCanvasElement for consistent processing downstream.
 * 
 * @param {any} src - The input image in any supported format
 * @returns {Promise<HTMLImageElement|HTMLCanvasElement>} Normalized image ready for processing
 * @throws {Error} If the source format is not supported
 */
function loadOriginalImage(src) {
    return new Promise((resolve, reject) => {
        try {
            // Handle File objects by creating a data URL
            if (src instanceof File) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const img = new Image();
                    img.crossOrigin = 'Anonymous';
                    img.src = e.target.result;
                    img.onload = () => resolve(img);
                    img.onerror = (err) => reject(new Error(`Failed to load image from file: ${err.message}`));
                };
                reader.onerror = (err) => reject(new Error(`FileReader error: ${err.message}`));
                reader.readAsDataURL(src);
                return;
            }

            // Directly resolve if the source is an HTMLImageElement
            if (src instanceof HTMLImageElement) {
                resolve(src);
                return;
            }

            // Handle HTMLCanvasElement, return the canvas directly
            if (src instanceof HTMLCanvasElement) {
                resolve(src); // return the canvas directly
                return;
            }

            // Handle ImageData by converting it to a canvas
            if (src instanceof ImageData) {
                const tempCanvas = document.createElement('canvas');
                tempCanvas.width = src.width;
                tempCanvas.height = src.height;
                const tempCtx = tempCanvas.getContext('2d');
                tempCtx.putImageData(src, 0, 0);
                resolve(tempCanvas); // return the created canvas
                return;
            }

            // Handle p5.Graphics or p5.Renderer, return the canvas directly
            if (src.elt && src.elt instanceof HTMLCanvasElement) {
                resolve(src.elt); // p5.Graphics or p5.Renderer object, return canvas
                return;
            }

            // Handle Q5.Image or Q5.Graphics, return the canvas directly
            if (src.canvas && src.canvas instanceof HTMLCanvasElement) {
                resolve(src.canvas); // Q5.Graphics or Q5.Image object, return canvas
                return;
            }

            // Handle OffscreenCanvas, convert it to an HTMLCanvasElement
            if (src.canvas instanceof OffscreenCanvas) {
                const tempCanvas = document.createElement('canvas');
                tempCanvas.width = src.canvas.width;
                tempCanvas.height = src.canvas.height;
                const tempCtx = tempCanvas.getContext('2d');
                tempCtx.drawImage(src.canvas, 0, 0);
                resolve(tempCanvas); // return the converted canvas
                return;
            }
            //Handle T5js
            if (src.element) {
                resolve(src.element);
                return;
            }
            // Handle URL strings by loading an image
            if (typeof src === 'string') {
                const img = new Image();
                img.crossOrigin = 'Anonymous';
                img.src = src;

                img.onload = () => resolve(img);
                img.onerror = (err) => {
                    reject(new Error(`Failed to load image: ${err.message}`));
                };
                return;
            }

            // Handle unexpected sources
            console.warn('Unsupported or invalid image source.');
            reject(new Error('Unsupported or invalid image source.'));
        } catch (error) {
            console.warn(`Error when loading image: ${error.message}`);
            reject(error);
        }
    });
}

/**
 * Cache for fetched color palettes to avoid redundant API calls.
 * This improves performance when processing multiple images with the same palette.
 */
let cachedPalette = { name: null, colors: null };

/**
 * Fetch a color palette from the Lospec API.
 * 
 * Lospec is a community database of pixel art color palettes. Using
 * established palettes ensures training data has authentic pixel art
 * color schemes that models can learn to recognize and reproduce.
 * 
 * The function caches fetched palettes to reduce API calls during
 * batch processing, which is important for generating large datasets.
 * 
 * POPULAR PALETTES FOR TRAINING:
 * - 'pico-8': 16 colors, classic fantasy console palette
 * - 'endesga-32': 32 colors, versatile general-purpose palette
 * - 'resurrect-64': 64 colors, comprehensive range for detailed art
 * - 'sweetie-16': 16 colors, pastel tones for softer aesthetics
 * 
 * @param {string} paletteName - The Lospec palette slug (e.g., 'pico-8')
 * @returns {Promise<Array<Array<number>>>} RGB color arrays [[r,g,b], ...]
 * @throws {Error} If the palette cannot be fetched from Lospec
 */
function fetchPalette(paletteName) {
    const paletteUrl = `https://lospec.com/palette-list/${paletteName}.json`;
    if (cachedPalette.name === paletteName) { return Promise.resolve(cachedPalette.colors); }
    return fetch(paletteUrl)
        .then(response => {
            if (!response.ok) throw new Error('Palette not found');
            return response.json();
        })
        .then(data => {
            const colors = data.colors.map(hexToRgb);
            // Cache the fetched palette
            cachedPalette.name = paletteName;
            cachedPalette.colors = colors;
            return colors;
        })
        .catch(error => {
            console.warn('Error fetching palette:', error);
            throw error;
        });

}

/**
 * Convert hexadecimal color string to RGB array.
 * 
 * This utility function converts hex color codes (common in palettes)
 * to RGB arrays needed for pixel manipulation. It handles both
 * 3-character and 6-character hex codes with or without '#' prefix.
 * 
 * @param {string} hex - Hex color code (e.g., '#FF0000' or 'FF0000')
 * @returns {Array<number>} RGB values as [red, green, blue] (0-255 range)
 */
function hexToRgb(hex) {
    hex = hex.replace('#', '');
    const bigint = parseInt(hex, 16);
    return [bigint >> 16 & 255, bigint >> 8 & 255, bigint & 255];
}

/**
 * Apply color palette quantization to image data.
 * 
 * This function reduces the image colors to a limited palette,
 * which is essential for creating authentic pixel art. It maps
 * each pixel to its nearest color in the target palette.
 * 
 * For training data, this ensures consistent color schemes that
 * models can learn to recognize as characteristic of pixel art.
 * 
 * @param {ImageData} imageData - Canvas image data to modify in-place
 * @param {Array<Array<number>>} paletteColors - Target palette as RGB arrays
 */
function applyPalette(imageData, paletteColors) {
    const data = imageData.data;
    for (let i = 0; i < data.length; i += 4) {
        const color = [data[i], data[i + 1], data[i + 2]];
        const [r, g, b] = findClosestPaletteColor(color, paletteColors);
        data[i] = r;
        data[i + 1] = g;
        data[i + 2] = b;
    }
}
/**
 * Apply Atkinson dithering algorithm for gentler error diffusion.
 * 
 * Atkinson dithering, developed by Bill Atkinson for early Macintosh
 * computers, diffuses only 75% of the quantization error (compared to
 * Floyd-Steinberg's 100%). This creates higher contrast but preserves
 * detail better in areas of similar tones.
 * 
 * CHARACTERISTICS:
 * - Better for high-contrast images and line art
 * - Preserves sharp edges better than Floyd-Steinberg
 * - Creates a distinctive retro computing aesthetic
 * - Good for training models to recognize vintage pixel art styles
 * 
 * ERROR DISTRIBUTION PATTERN:
 *     *   1/8  1/8
 * 1/8 1/8 1/8
 *     1/8
 * 
 * Where * is the current pixel being processed.
 * 
 * @param {ImageData} imageData - Image data to process in-place
 * @param {number} width - Image width in pixels
 * @param {number} height - Image height in pixels
 * @param {number} strength - Dithering strength (0-1 range)
 * @param {Array<Array<number>>} paletteColors - Target color palette
 * @returns {ImageData} Modified image data with dithering applied
 */
function atkinsonDithering(imageData, width, height, strength, paletteColors) {
    const data = imageData.data;
    const errorBuffer = new Float32Array(data.length);

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const idx = (y * width + x) * 4;

            // Get original color and add accumulated error
            let r = data[idx] + errorBuffer[idx];
            let g = data[idx + 1] + errorBuffer[idx + 1];
            let b = data[idx + 2] + errorBuffer[idx + 2];

            const oldColor = [r, g, b];

            // Quantize the pixel to the nearest palette color
            const newColor = findClosestPaletteColor(oldColor, paletteColors);

            // Update the image data with the new color
            data[idx] = newColor[0];
            data[idx + 1] = newColor[1];
            data[idx + 2] = newColor[2];

            // Calculate the quantization error
            const quantError = [
                (r - newColor[0]) * strength,
                (g - newColor[1]) * strength,
                (b - newColor[2]) * strength
            ];

            // Distribute the error to neighboring pixels
            distributeError(errorBuffer, x + 1, y, quantError, (1 / 8), width, height);
            distributeError(errorBuffer, x + 2, y, quantError, (1 / 8), width, height);
            distributeError(errorBuffer, x - 1, y + 1, quantError, (1 / 8), width, height);
            distributeError(errorBuffer, x, y + 1, quantError, (1 / 8), width, height);
            distributeError(errorBuffer, x + 1, y + 1, quantError, (1 / 8), width, height);
            distributeError(errorBuffer, x, y + 2, quantError, (1 / 8), width, height);
        }
    }
    return imageData;
}

/**
 * Apply Floyd-Steinberg dithering for classic error diffusion.
 * 
 * Floyd-Steinberg is the most widely used error diffusion algorithm.
 * It distributes quantization error to neighboring pixels in a specific
 * pattern, creating smooth gradients even with limited colors.
 * 
 * CHARACTERISTICS:
 * - Excellent for photographs and gradients
 * - Creates organic, non-repetitive patterns
 * - Can produce "worm" artifacts in flat color areas
 * - Industry standard for pixel art conversion
 * 
 * ERROR DISTRIBUTION PATTERN:
 *     * 7/16
 * 3/16 5/16 1/16
 * 
 * Where * is the current pixel. The fractions show how much
 * error is distributed to each neighboring pixel.
 * 
 * This algorithm is ideal for training data because it produces
 * results similar to hand-crafted pixel art with careful shading.
 * 
 * @param {ImageData} imageData - Image data to process in-place
 * @param {number} width - Image width in pixels
 * @param {number} height - Image height in pixels
 * @param {number} strength - Dithering strength (0-1 range)
 * @param {Array<Array<number>>} paletteColors - Target color palette
 * @returns {ImageData} Modified image data with dithering applied
 */
function floydSteinbergDithering(imageData, width, height, strength, paletteColors) {
    const data = imageData.data;
    const errorBuffer = new Float32Array(data.length);

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const idx = (y * width + x) * 4;

            // Get original color and add accumulated error
            let r = data[idx] + errorBuffer[idx];
            let g = data[idx + 1] + errorBuffer[idx + 1];
            let b = data[idx + 2] + errorBuffer[idx + 2];

            const oldColor = [r, g, b];

            // Quantize the pixel to the nearest palette color
            const newColor = findClosestPaletteColor(oldColor, paletteColors);

            // Update the image data with the new color
            data[idx] = newColor[0];
            data[idx + 1] = newColor[1];
            data[idx + 2] = newColor[2];

            // Calculate the quantization error
            const quantError = [
                (r - newColor[0]) * strength,
                (g - newColor[1]) * strength,
                (b - newColor[2]) * strength
            ];

            // Distribute the error to neighboring pixels using Floyd-Steinberg coefficients
            distributeError(errorBuffer, x + 1, y, quantError, DitheringCoefficients.FLOYD_STEINBERG.RIGHT, width, height);
            distributeError(errorBuffer, x - 1, y + 1, quantError, DitheringCoefficients.FLOYD_STEINBERG.BOTTOM_LEFT, width, height);
            distributeError(errorBuffer, x, y + 1, quantError, DitheringCoefficients.FLOYD_STEINBERG.BOTTOM, width, height);
            distributeError(errorBuffer, x + 1, y + 1, quantError, DitheringCoefficients.FLOYD_STEINBERG.BOTTOM_RIGHT, width, height);
        }
    }
    return imageData;
}

/**
 * Apply ordered dithering using a Bayer matrix pattern.
 * 
 * Ordered dithering uses a fixed threshold matrix to determine whether
 * to round colors up or down. This creates predictable, repeating patterns
 * that are useful for consistent training data generation.
 * 
 * CHARACTERISTICS:
 * - Creates regular, predictable patterns
 * - No error accumulation (each pixel processed independently)
 * - Good for flat colors and gradients
 * - Produces consistent results across identical inputs
 * - Ideal for training models to recognize pattern-based dithering
 * 
 * The Bayer matrix provides threshold values that create the
 * characteristic crosshatch pattern of ordered dithering.
 * 
 * @param {ImageData} imageData - Image data to process in-place
 * @param {number} width - Image width in pixels
 * @param {number} height - Image height in pixels
 * @param {number} strength - Dithering strength (0-1 range)
 * @param {Array<Array<number>>} paletteColors - Target color palette
 * @param {Array<Array<number>>} bayerMatrix - Threshold matrix for pattern
 * @returns {ImageData} Modified image data with ordered dithering
 */
function orderedDithering(imageData, width, height, strength, paletteColors, bayerMatrix) {
    const data = imageData.data;
    const matrixSize = bayerMatrix.length;

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const idx = (y * width + x) * 4;
            const oldColor = [data[idx], data[idx + 1], data[idx + 2]];

            const threshold = ((bayerMatrix[y % matrixSize][x % matrixSize] + 0.5) / (matrixSize * matrixSize)) * 255;

            // Adjust color based on Bayer matrix threshold
            // The threshold shifts the color before quantization, creating the dither pattern
            let adjustedColor = [
                oldColor[0] + (threshold - DitheringCoefficients.ORDERED_THRESHOLD_CENTER) * strength,
                oldColor[1] + (threshold - DitheringCoefficients.ORDERED_THRESHOLD_CENTER) * strength,
                oldColor[2] + (threshold - DitheringCoefficients.ORDERED_THRESHOLD_CENTER) * strength
            ];

            // Quantize the adjusted color
            const newColor = findClosestPaletteColor(adjustedColor, paletteColors);

            data[idx] = newColor[0];
            data[idx + 1] = newColor[1];
            data[idx + 2] = newColor[2];
        }
    }
    return imageData;
}

/**
 * Distribute quantization error to a neighboring pixel.
 * 
 * This helper function is used by error diffusion dithering algorithms
 * to propagate color quantization errors to nearby pixels. The error
 * accumulation creates the smooth gradients characteristic of these methods.
 * 
 * The function safely handles boundary conditions to prevent buffer overflows.
 * 
 * @param {Float32Array} buffer - Error accumulation buffer
 * @param {number} x - Target pixel X coordinate
 * @param {number} y - Target pixel Y coordinate
 * @param {Array<number>} quantError - RGB error values to distribute
 * @param {number} factor - Fraction of error to apply (0-1 range)
 * @param {number} width - Image width for bounds checking
 * @param {number} height - Image height for bounds checking
 */
function distributeError(buffer, x, y, quantError, factor, width, height) {
    if (x < 0 || x >= width || y < 0 || y >= height) return;
    const idx = (y * width + x) * 4;
    buffer[idx] += quantError[0] * factor;
    buffer[idx + 1] += quantError[1] * factor;
    buffer[idx + 2] += quantError[2] * factor;
}

/**
 * Find the nearest color in a palette using Euclidean distance.
 * 
 * This function maps an arbitrary RGB color to its closest match
 * in a limited palette. The quality of this mapping directly affects
 * the visual quality of the pixel art output.
 * 
 * The function uses Euclidean distance in RGB space, which is
 * computationally efficient though not perceptually uniform.
 * For training data, consistency is more important than perfect
 * perceptual accuracy.
 * 
 * OPTIMIZATION NOTE:
 * For large palettes or batch processing, this could be optimized
 * with a k-d tree or octree structure.
 * 
 * @param {Array<number>} color - RGB color to match [r, g, b]
 * @param {Array<Array<number>>} palette - Available colors [[r,g,b], ...]
 * @returns {Array<number>} Closest palette color [r, g, b]
 */
function findClosestPaletteColor(color, palette) {
    let closestColor = palette[0];
    let closestDistance = colorDistance(color, closestColor);

    for (let i = 1; i < palette.length; i++) {
        const currentDistance = colorDistance(color, palette[i]);
        if (currentDistance < closestDistance) {
            closestDistance = currentDistance;
            closestColor = palette[i];
        }
    }

    return closestColor;
}

/**
 * Calculate Euclidean distance between two RGB colors.
 * 
 * This measures color similarity for palette matching. While not
 * perceptually uniform (human vision is more sensitive to green),
 * Euclidean distance is fast and produces consistent results for
 * training data generation.
 * 
 * The squared distance is returned (without square root) for
 * efficiency, since we only need relative distances for comparison.
 * 
 * ALTERNATIVE APPROACHES:
 * - Weighted Euclidean: Weight green channel higher (matches human vision)
 * - LAB color space: More perceptually uniform but computationally expensive
 * - Delta E: Industry standard for color difference but complex
 * 
 * @param {Array<number>} color1 - First RGB color [r, g, b]
 * @param {Array<number>} color2 - Second RGB color [r, g, b]
 * @returns {number} Squared Euclidean distance between colors
 */
function colorDistance(color1, color2) {
    // Use squared Euclidean distance (skip sqrt for efficiency)
    const rDiff = color1[0] - color2[0];
    const gDiff = color1[1] - color2[1];
    const bDiff = color1[2] - color2[2];
    return rDiff * rDiff + gDiff * gDiff + bDiff * bDiff;
}
