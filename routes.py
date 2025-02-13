import os
from dotenv import load_dotenv
from typing import List
from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm

from jose import JWTError, jwt
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from security import verify_password, get_password_hash, create_access_token, oauth2_scheme
from models import User, ReferralCode
# from database import get_db, get_session
from database import get_session
from schemas import (
    UserCreate,
    Token,
    TokenData,
    ReferralCodeCreate,
    ReferralCodeResponse,
    RefereeResponse
)

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise Exception("SECRET_KEY is not set")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_TIME", 30))

#https://stackoverflow.com/questions/68360687/sqlalchemy-asyncio-orm-how-to-query-the-database
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).filter(User.email == email))
    
    return result.scalars().first()

# https://stackoverflow.com/questions/68811220/handling-the-token-expiration-in-fastapi
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
         status_code=status.HTTP_401_UNAUTHORIZED,
         detail="Could not validate credentials",
         headers={"WWW-Authenticate": "Bearer"},
    )
    try:
         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
         email: str = payload.get("sub")
         if email is None:
             raise credentials_exception
         token_data = TokenData(email=email)
    except JWTError:
         raise credentials_exception
    user = await get_user_by_email(db, email=token_data.email)
    if user is None:
         raise credentials_exception
    return user


router = APIRouter()

@router.post("/register", response_model=Token, summary="Регистрация пользователя")
async def register(user: UserCreate, db: AsyncSession = Depends(get_session)):
    """
    Форма регистрации пользователя.

    - **user**: логин пароль опционально указывается реферальный код.
    - **db**: Сессия подключения к бд.

    **Пример запроса:**

        POST /token  -d '{"email": "22@ex.com", "password": "22", "referral_code": ""}'

    **Возвращает** access_token.
    """
    db_user = await get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    
    referrer = None
    # проверяем код реферера
    print('\n\n\n\n')
    print(referrer)
    print('\n\n\n\n')
    if user.referral_code:
        statement = select(ReferralCode).filter(
            ReferralCode.code == user.referral_code,
            ReferralCode.is_active == True
        )
        result = await db.execute(statement)
        referral = result.scalars().first()
        if not referral:
            raise HTTPException(status_code=400, detail="Неверный реферальный код")
        if referral.expiry < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Срок действия реферального кода истёк")
        referrer = referral.owner

    hashed_password = get_password_hash(user.password)
    print('\n\n\n\n')
    print(hashed_password)
    print('\n\n\n\n')
    new_user = User(
        email=user.email,
        hashed_password=hashed_password,
        referrer_id=referrer.id if referrer else None
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
         data={"sub": new_user.email},
         expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/token", response_model=Token, summary="Получить JWT токен")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_session)):
    """
    Авторизация пользователя.

    - **form-data**: данные авторизации.
    - **db**: Сессия подключения к бд.

    **Пример запроса:**

        POST /token  -d 'username=123@ex.com&password=123'

    **Возвращает** access_token.
    """
    user = await get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверный логин или пароль")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
         data={"sub": user.email},
         expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/referral-code", response_model=ReferralCodeResponse, summary="Создать реферальный код")
async def create_referral_code(
    referral_data: ReferralCodeCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Создание реферального кода.

    - **referral_data**: дата окончания кода в формате utc.
    - **current_user**: Пользователь полученный из сессии.
    - **db**: Сессия подключения к бд.

    **Пример запроса:**

        POST /referral-code -d '{"expiry": "2022-02-22T22:22:22.937Z"}'

    **Возвращает** данные о коде.

    Пользователь должен быть авторизован.
    """
    statement = select(ReferralCode).filter(
        ReferralCode.owner_id == current_user.id,
        ReferralCode.is_active == True
    )
    result = await db.execute(statement)
    existing_code = result.scalars().first()
    
    if existing_code:
        raise HTTPException(status_code=400, detail="У вас уже есть активный реферальный код")
    
    # генерим реф-код
    while True:
        code = secrets.token_urlsafe(6)
        
        result = await db.execute(select(ReferralCode).filter(ReferralCode.code == code))
        existing_code = result.scalars().first()
        if not existing_code:
            break

    new_code = ReferralCode(
         code = code,
         owner_id = current_user.id,
         expiry = referral_data.expiry.replace(tzinfo=timezone.utc),
         is_active = True
    )
    db.add(new_code)
    await db.commit()
    await db.refresh(new_code)
    return ReferralCodeResponse(code=new_code.code, expiry=new_code.expiry, is_active=new_code.is_active)


@router.delete("/referral-code", response_model=dict, summary="Удалить/деактивировать реферальный код")
async def delete_referral_code(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Удаление реферального кода.

    - **current_user**: Пользователь полученный из сессии.
    - **db**: Сессия подключения к бд.

    **Пример запроса:**

        DELETE /referral-code

    **Возвращает** сообщение об успешном удалении.

    Пользователь должен быть авторизован.
    """
    statement = select(ReferralCode).filter(
        ReferralCode.owner_id == current_user.id,
        ReferralCode.is_active == True
    )
    result = await db.execute(statement)
    referral = result.scalars().first()
    
    if not referral:
        raise HTTPException(status_code=404, detail="Активный реферальный код не найден")
    referral.is_active = False
    await db.commit()
    return {"detail": "Реферальный код деактивирован"}


@router.get("/referral-code", response_model=ReferralCodeResponse, summary="Получить реферальный код по email")
async def get_referral_code(
    email: str = Query(..., description="Email реферера"),
    db: AsyncSession = Depends(get_session)
):
    """
    Функция получения реферального кода по email.

    - **email**: EMAIL пользователя, на который высылается код.
    - **db**: Сессия подключения к бд.

    **Пример запроса:**

        GET /referral-code?email=1@ex.com

    
    По факту функция не реализована, нужно дописать логику и **возвращает** просто данные о коде.
    """
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    statement = select(ReferralCode).filter(
         ReferralCode.owner_id == user.id,
         ReferralCode.is_active == True
    )
    result = await db.execute(statement)
    referral = result.scalars().first()
    if not referral:
        raise HTTPException(status_code=404, detail="Активный реферальный код для данного пользователя не найден")
    
    # тут какая то логика отправки email ...... мне лень писать
    
    return ReferralCodeResponse(code=referral.code, expiry=referral.expiry, is_active=referral.is_active)


@router.get("/referrals", response_model=List[RefereeResponse], summary="Получить список рефералов")
async def get_referrals(
    referrer_id: int | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Возвращает список рефералов для указанного пользователя.

    Если параметр referrer_id не передан, то функция использует id текущего пользователя, полученного через get_current_user.

    - **referrer_id**: ID пользователя, для которого нужно получить рефералов.
    - **current_user**: Пользователь полученный из сессиии.
    - **db**: Сессия подключения к бд.

    **Пример запроса:**

        GET /referrals?referrer_id=1

    **Возвращает** список рефералов.
    
    Если параметр referrer_id не указан, то используется id аутентифицированного пользователя.
    """
    if referrer_id is None:
        referrer_id = current_user.id
    # referees = await db.query(User).filter(User.referrer_id == referrer_id).all()
    
    statement = select(User).filter(
        User.referrer_id == referrer_id
    )
    result = await db.execute(statement)
    referees = result.scalars().all()
    
    return [RefereeResponse(id=user.id, email=user.email) for user in referees]
