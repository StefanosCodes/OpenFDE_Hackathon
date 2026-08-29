from fastapi import HTTPException, status


def not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)
