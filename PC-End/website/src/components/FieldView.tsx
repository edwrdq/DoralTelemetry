import { useRef, useState, useEffect } from "react";
import type { Message } from "../App";
import Field from "../assets/field.jpeg"
const FieldView: React.FC<{
  data: Message | null;
}> = ({ data }) => {
  // References for drawing
  const imageRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Track when the image is actually loaded
  const [imageLoaded, setImageLoaded] = useState(false);

  // Effect to draw the field whenever detections or image loaded state changes
  useEffect(() => {
    // Debug: log data and imageLoaded state
    if (!imageLoaded || !canvasRef.current) return;
    // Directly draw the field with the current pose
    const canvas = canvasRef.current;
    if (data && canvas) {
      drawField(canvas, data);
    }
  }, [data, imageLoaded]);

  // Function to draw the field and robot with a specific pose
  const drawField = (
    canvas: HTMLCanvasElement,
    msg: Message,
  ) => {
    const image = imageRef.current;
    const container = containerRef.current;

    if (!canvas || !image || !container) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Get container dimensions
    const containerRect = container.getBoundingClientRect();
    canvas.width = containerRect.width;
    canvas.height = containerRect.height;

    // Field dimensions in inches
    const FIELD_WIDTH_INCHES = 144;
    const FIELD_HEIGHT_INCHES = 144;

    // Robot dimensions in inches (18x18 inch square robot)
    const ROBOT_SIZE_INCHES = 18;

    // Calculate scaling factor to convert inches to pixels
    const scaleX = containerRect.width / FIELD_WIDTH_INCHES;
    const scaleY = containerRect.height / FIELD_HEIGHT_INCHES;
    const scale = Math.min(scaleX, scaleY); // Use the smaller scale to maintain aspect ratio

    // Calculate offset to center the field
    const offsetX = (containerRect.width - FIELD_WIDTH_INCHES * scale) / 2;
    const offsetY = (containerRect.height - FIELD_HEIGHT_INCHES * scale) / 2;

    // Function to convert field coordinates (inches, origin at center, y-up)
    // to canvas coordinates (pixels, origin at top-left, y-down)
    const fieldToCanvas = (fieldX: number, fieldY: number) => {
      // 1. Translate from field center origin to top-left origin
      const centeredX = fieldX + FIELD_WIDTH_INCHES / 2;
      const centeredY = FIELD_HEIGHT_INCHES / 2 - fieldY; // Invert Y-axis

      // 2. Scale from inches to pixels
      const pixelX = centeredX * scale + offsetX;
      const pixelY = centeredY * scale + offsetY;

      return { x: pixelX, y: pixelY };
    };

    // Clear the canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Reset global alpha after drawing detections
    ctx.globalAlpha = 1.0;

    const { x, y, theta } = msg;

    // Convert robot position from field to canvas coordinates
    const canvasPos = fieldToCanvas(x, y);

    // Calculate robot size in pixels
    const robotSizePixels = ROBOT_SIZE_INCHES * scale;
    const halfSize = robotSizePixels / 2;

    // Define robot corners relative to its center position (in canvas pixel space)
    const corners = [
      { x: -halfSize, y: -halfSize }, // Top-left
      { x: halfSize, y: -halfSize }, // Top-right
      { x: halfSize, y: halfSize }, // Bottom-right
      { x: -halfSize, y: halfSize }, // Bottom-left
    ];

    // Rotate and position the robot corners
    // For CCW rotation where 0 = up (north)
    const rotatedCorners = corners.map((corner) => {
      // Convert theta from degrees to radians for trigonometric functions
      const thetaRadians = theta * (Math.PI / 180);

      // Rotate the corner around robot center - using counterclockwise rotation formula
      const cosTheta = Math.cos(thetaRadians);
      const sinTheta = Math.sin(thetaRadians);

      const rotatedX = corner.x * cosTheta + corner.y * sinTheta;
      const rotatedY = -corner.x * sinTheta + corner.y * cosTheta;

      // Translate to robot position on canvas
      return {
        x: canvasPos.x + rotatedX,
        y: canvasPos.y + rotatedY,
      };
    });

    // Draw robot body
    ctx.fillStyle = "rgba(128, 128, 128, 0.7)";
    ctx.beginPath();
    ctx.moveTo(rotatedCorners[0].x, rotatedCorners[0].y);
    for (let i = 1; i < rotatedCorners.length; i++) {
      ctx.lineTo(rotatedCorners[i].x, rotatedCorners[i].y);
    }
    ctx.closePath();
    ctx.fill();

    // Draw robot outline
    ctx.strokeStyle = "rgba(0, 0, 0, 0.8)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(rotatedCorners[0].x, rotatedCorners[0].y);
    for (let i = 1; i < rotatedCorners.length; i++) {
      ctx.lineTo(rotatedCorners[i].x, rotatedCorners[i].y);
    }
    ctx.closePath();
    ctx.stroke();

    // Draw blue front face (0-1 side to be on top when the robot is at 0° orientation)
    ctx.strokeStyle = "rgba(0, 102, 255, 1.0)";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(rotatedCorners[0].x, rotatedCorners[0].y);
    ctx.lineTo(rotatedCorners[1].x, rotatedCorners[1].y);
    ctx.stroke();

    // Draw a small dot at the robot center for reference
    ctx.fillStyle = "rgba(255, 0, 0, 0.7)";
    ctx.beginPath();
    ctx.arc(canvasPos.x, canvasPos.y, 2, 0, Math.PI * 2);
    ctx.fill();
  };

  // Handle image load
  useEffect(() => {
    const image = imageRef.current;
    if (!image) return;

    const handleImageLoad = () => {
      setImageLoaded(true);
    };

    // Add event listener
    image.addEventListener("load", handleImageLoad);

    // If image is already loaded
    if (image.complete && image.naturalWidth) {
      handleImageLoad();
    }

    // Cleanup
    return () => {
      image.removeEventListener("load", handleImageLoad);
    };
  }, []);

  // // Effect to handle resize events
  // useEffect(() => {
  //   const container = containerRef.current;
  //   const image = imageRef.current;

  //   if (!container || !image) return;

  //   // Handle resize
  //   const handleResize = () => {
  //     if (canvasRef.current && data) {
  //       drawField(canvasRef.current, data);
  //     }
  //   };

  //   // Create a ResizeObserver for better size change detection
  //   const resizeObserver = new ResizeObserver(() => {
  //     handleResize();
  //   });

  //   // Add resize listeners
  //   window.addEventListener("resize", handleResize);
  //   resizeObserver.observe(container);
  //   resizeObserver.observe(image);

  //   // Cleanup on unmount
  //   return () => {
  //     window.removeEventListener("resize", handleResize);
  //     resizeObserver.disconnect();
  //   };
  // }, [data]);

  return (
    <div className="">
      <div
        ref={containerRef}
        className="relative w-full aspect-square"
      >
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="relative w-full h-full">
            <img
              ref={imageRef}
              src={Field}
              alt="VEX Field View"
              className="absolute top-0 left-0 w-full h-full object-contain"
            />
            <canvas
              ref={canvasRef}
              className="absolute top-0 left-0 w-full h-full"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default FieldView;
