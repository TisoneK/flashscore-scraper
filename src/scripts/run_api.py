#!/usr/bin/env python3
import uvicorn


def main() -> None:
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        factory=False,
    )


if __name__ == "__main__":
    main()


