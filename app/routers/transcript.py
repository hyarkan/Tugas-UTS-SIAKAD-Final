"""Week 10 transcript routes. Demo header identity is NOT production authentication."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.grades import get_current_dosen
from app.services.transcript import get_transcript
from app.services.transcript_pdf import render_transcript_html, render_transcript_pdf

router = APIRouter(tags=['Transkrip Akademik - Minggu 10'])


def _load(nim: str, db: Session) -> dict:
    data = get_transcript(db, nim)
    if data is None:
        raise HTTPException(status_code=404, detail='Mahasiswa tidak ditemukan.')
    return data


@router.get('/api/nilai/{nim}/transkrip')
def transcript(nim: str, db: Session = Depends(get_db), _actor: int = Depends(get_current_dosen)):
    return _load(nim, db)


@router.get('/api/nilai/{nim}/transkrip/html', response_class=HTMLResponse)
def transcript_html(nim: str, db: Session = Depends(get_db), _actor: int = Depends(get_current_dosen)):
    return HTMLResponse(render_transcript_html(_load(nim, db)))


@router.get('/api/nilai/{nim}/transkrip/pdf')
def transcript_pdf(nim: str, db: Session = Depends(get_db), _actor: int = Depends(get_current_dosen)):
    content = render_transcript_pdf(_load(nim, db))
    return Response(content, media_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="transkrip_{nim}.pdf"',
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
