import { ImageResponse } from "next/og";

export const size = {
  width: 32,
  height: 32,
};
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "transparent",
        }}
      >
        <svg
          width="32"
          height="32"
          viewBox="0 0 32 32"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* 盾牌主体 - 高级渐变 */}
          <defs>
            <linearGradient id="shieldGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#6366f1" />
              <stop offset="50%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#0ea5e9" />
            </linearGradient>
            <linearGradient id="boltGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#fbbf24" />
              <stop offset="100%" stopColor="#f59e0b" />
            </linearGradient>
          </defs>
          {/* 盾牌外形 */}
          <path
            d="M16 2L4 7v8c0 7.73 5.12 14.12 12 16 6.88-1.88 12-8.27 12-16V7L16 2z"
            fill="url(#shieldGrad)"
          />
          {/* 盾牌高光 */}
          <path
            d="M16 2L4 7v8c0 7.73 5.12 14.12 12 16V2z"
            fill="white"
            opacity="0.15"
          />
          {/* 闪电符号 */}
          <path
            d="M18.5 8L12 17h4l-2.5 7L20 15h-4l2.5-7z"
            fill="url(#boltGrad)"
          />
        </svg>
      </div>
    ),
    {
      ...size,
    }
  );
}
