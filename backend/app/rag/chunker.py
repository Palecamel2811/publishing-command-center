"""
Document chunking strategy optimized for music publishing documents.

Handles:
- Split sheets (parties, shares, PRO assignments)
- Royalty statements (tables, periods, platform breakdowns)
- Contracts (clauses, terms, definitions)
- DSP reports (usage metrics, revenue breakdowns)

Uses semantic boundary-aware chunking with metadata extraction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ChunkMetadata:
    """Structured metadata extracted during chunking."""
    doc_type: str = "unknown"
    work_title: str | None = None
    parties: list[str] = field(default_factory=list)
    shares: list[tuple[str, float]] = field(default_factory=list)
    period_start: str | None = None
    period_end: str | None = None
    platform: str | None = None
    royalty_type: str | None = None
    clause_type: str | None = None
    table_header: str | None = None
    line_start: int = 1
    line_end: int = 1



class LegalFinancialChunker:
    """
    Chunking strategy for music publishing documents.
    
    Key design decisions:
    - Preserves split sheet structures: never split a party-share row
    - Aligns chunks to contract clauses, not just character boundaries
    - Extracts structured metadata during chunking for better filtering
    - Uses semantic headers to maintain context across chunks
    """

    # Regex patterns for music publishing domain
    PARTY_SHARE_RE = re.compile(
        r"^\s*\|?\s*([A-Za-z\s&.\-():]{2,50}?)\s*(?:[|/:]|(?:\.{2,}))\s*"  # Party name
        r"(\d+(?:\.\d+)?)\s*%\s*"                                           # Percentage
        r"(?:\|\s*([^|\n%]*)\|?|([^|\n%]*))\s*$",                            # Optional role/notes
        re.MULTILINE,
    )
    CLAUSE_HEADER_RE = re.compile(
        r"^(?:Section|Article|Clause|§)\s*[\d.\s]+\s*[:–-]?\s*(.+)$",
        re.MULTILINE,
    )
    PERIOD_RE = re.compile(
        r"(Q[1-4]\s*\d{4}|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}"
        r"(?:\s*-\s*(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})?\b)",
        re.IGNORECASE,
    )
    WORK_TITLE_RE = re.compile(
        r'(?:Single Title|Song Title|Work Title|Composition Title|Composition|Work|Song|Title)[ \t]*[:–-]?[ \t]*["“]?([^"”\n|,:–-]{2,100})["”]?'
        r'|^["“]([^"”\n\r]{2,50})["”]\s*$'
        r'|["“]([^"”\n\r]{2,50})["”]\s*\n\s*(?:Performed by|recorded by|by)',
        re.IGNORECASE | re.MULTILINE,
    )

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        min_chunk_size: int = 128,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def _clean_work_title(self, title: str | None) -> str | None:
        if not title:
            return None
        title_clean = title.strip().strip('"').strip('“').strip('”')
        # Exclude headers / metadata tags starting with &
        if title_clean.startswith("&"):
            m = re.search(r"Single Title\s*[:–-]?\s*(.*?)\s*(?:Album Title|Primary Artist|ISRC|ISWC|$)", title_clean, re.IGNORECASE)
            if m and len(m.group(1).strip()) > 1:
                return m.group(1).strip()
            return None
        # Strip common noise suffixes if found from filenames or headings
        for noise in ["Split Sheet Report", "Split Sheet", "Royalty Statement", "Sync Contract", "Statement Report", "Report", "Statement", "Splits"]:
            pattern = re.compile(rf"[ \t_-]*\b{re.escape(noise)}\b[ \t_-]*.*", re.IGNORECASE)
            title_clean = pattern.sub("", title_clean).strip()
        title_clean = re.sub(r"[ \t_-]+\b(LUV|L\.U\.V\.|v\d+)\b.*$", "", title_clean, flags=re.IGNORECASE).strip()
        if len(title_clean) >= 2:
            return title_clean.title() if title_clean.isupper() or "_" in title_clean else title_clean
        return None

    def chunk_document(
        self,
        text: str,
        doc_type: str = "unknown",
        source_filename: str = "",
        work_id: str | None = None,
    ) -> list[tuple[str, ChunkMetadata]]:
        """
        Chunk a document into contextually meaningful segments.
        
        Returns list of (content, metadata) tuples.
        """
        # Detect structure and chunk accordingly
        if "split" in doc_type.lower() or "party" in doc_type.lower():
            return self._chunk_split_sheet(text, doc_type, source_filename, work_id)
        elif "royalty" in doc_type.lower() or "statement" in doc_type.lower():
            return self._chunk_royalty_statement(text, doc_type, source_filename, work_id)
        elif any(k in doc_type.lower() for k in ["contract", "license", "agreement"]):
            return self._chunk_contract(text, doc_type, source_filename, work_id)
        else:
            return self._chunk_generic(text, doc_type, source_filename, work_id)

    def _chunk_split_sheet(
        self, text: str, doc_type: str, source: str, work_id: str | None
    ) -> list[tuple[str, ChunkMetadata]]:
        """
        Split sheet chunking: preserve party-share pairs as atomic units.
        
        A chunk always contains a complete party entry: name + share + notes.
        """
        metadata = ChunkMetadata(doc_type=doc_type)
        
        # Extract work title
        work_match = self.WORK_TITLE_RE.search(text)
        if work_match:
            matched_title = next((g for g in work_match.groups() if g), None)
            metadata.work_title = self._clean_work_title(matched_title)
        elif work_id:
            metadata.work_title = work_id

        # Extract all party-share entries
        parties_data = []
        for match in self.PARTY_SHARE_RE.finditer(text):
            name = match.group(1).strip()
            share = float(match.group(2))
            notes = match.group(3).strip() if match.group(3) else None
            metadata.parties.append(name)
            metadata.shares.append((name, share))
            parties_data.append({
                "name": name,
                "share": share,
                "notes": notes,
            })

        # Extract periods
        period_matches = self.PERIOD_RE.findall(text)
        if len(period_matches) >= 2:
            metadata.period_start = period_matches[0]
            metadata.period_end = period_matches[1]
        elif period_matches:
            metadata.period_start = period_matches[0]

        # Build chunks: group parties in logical groups
        chunks: list[tuple[str, ChunkMetadata]] = []
        
        if len(parties_data) <= 3:
            # Small split sheets: single chunk with full context
            header = f"Document: {source}\nType: Split Sheet\n"
            if metadata.work_title:
                header += f"Work: {metadata.work_title}\n"
            body = "Parties and Shares:\n"
            for p in parties_data:
                line = f"  {p['name']}: {p['share']}%"
                if p['notes']:
                    line += f" ({p['notes']})"
                body += line + "\n"
            chunks.append((header + body, metadata))
        else:
            # Large split sheets: split into groups of 3-4 parties
            header = f"Document: {source}\nType: Split Sheet"
            if metadata.work_title:
                header += f"\nWork: {metadata.work_title}"
            
            for i in range(0, len(parties_data), 3):
                group = parties_data[i:i+3]
                chunk_text = header + "\n\n"
                chunk_text += "Parties:\n"
                for p in group:
                    line = f"  • {p['name']}: {p['share']}%"
                    if p['notes']:
                        line += f" — {p['notes']}"
                    chunk_text += line + "\n"
                chunks.append((chunk_text, ChunkMetadata(**{
                    k: v for k, v in metadata.__dict__.items() if k != "parties"
                })))
            
            # Add total verification chunk
            total_share = sum(p['share'] for p in parties_data)
            total_chunk = header + "\n\n" + (
                f"Total Verified Share: {total_share}%\n"
                f"All Parties ({len(parties_data)}): {', '.join(p['name'] for p in parties_data)}"
            )
            chunks.append((total_chunk, metadata))

        # Filter valid sized chunks
        result = [c for c in chunks if len(c[0]) >= self.min_chunk_size]
        if not result:
            return self._chunk_generic(text, doc_type, source, work_id)
        elif len(text) > 800:
            extra_chunks = self._chunk_generic(text, doc_type, source, work_id)
            result.extend(extra_chunks)
        
        return result

    def _chunk_royalty_statement(
        self, text: str, doc_type: str, source: str, work_id: str | None
    ) -> list[tuple[str, ChunkMetadata]]:
        """
        Royalty statement chunking: preserve table rows and period groupings.
        
        Strategy:
        1. Extract period ranges
        2. Group entries by platform/period
        3. Ensure each chunk has context (statement header, period)
        """
        metadata = ChunkMetadata(doc_type=doc_type)

        # Extract work title
        work_match = self.WORK_TITLE_RE.search(text)
        if work_match:
            matched_title = next((g for g in work_match.groups() if g), None)
            metadata.work_title = self._clean_work_title(matched_title)
        elif work_id:
            metadata.work_title = work_id

        # Extract periods
        period_matches = self.PERIOD_RE.findall(text)
        if len(period_matches) >= 2:
            metadata.period_start = period_matches[0]
            metadata.period_end = period_matches[1]
        elif period_matches:
            metadata.period_start = period_matches[0]

        # Extract royalty types
        royalty_patterns = re.findall(
            r"(?:Mechanical|Performance|Sync|Neighboring|Print|Other)\s+(?:Rights?)?",
            text,
            re.IGNORECASE,
        )
        if royalty_patterns:
            metadata.royalty_type = royalty_patterns[0]

        # Extract platforms mentioned
        platforms = re.findall(
            r"\b(Spotify|Apple\s*(?:Music|Store)|YouTube|TikTok|Amazon\s*Music|"
            r"Deezer|Pandora|iHeartRadio)\b",
            text,
            re.IGNORECASE,
        )
        if platforms:
            metadata.platform = platforms[0]

        # Split on major section breaks or periods
        sections = re.split(r"\n\n+", text)
        sections = [s.strip() for s in sections if len(s.strip()) > 20]

        if not sections:
            return [self._fallback_chunk(text, metadata)]

        chunks: list[tuple[str, ChunkMetadata]] = []
        
        # Add header context to each chunk
        header = f"Source: {source}\nType: {doc_type}\n"
        if metadata.work_title:
            header += f"Work: {metadata.work_title}\n"
        if metadata.period_start:
            header += f"Period: {metadata.period_start}\n"

        current_chunk = header
        current_meta = ChunkMetadata(**metadata.__dict__)
        
        for section in sections:
            if len(current_chunk + section) > self.chunk_size:
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append((current_chunk, ChunkMetadata(**current_meta.__dict__)))
                current_chunk = header + section
            else:
                current_chunk += "\n\n" + section

        if len(current_chunk) >= self.min_chunk_size:
            chunks.append((current_chunk, ChunkMetadata(**current_meta.__dict__)))

        return chunks if chunks else [self._fallback_chunk(text, metadata)]

    def _classify_clause(self, title: str) -> str:
        title = title.lower()
        if "definition" in title: return "definition"
        if "grant" in title: return "grant_of_rights"
        if "royalty" in title or "payment" in title: return "financial"
        if "term" in title: return "term"
        return "general"

    def _chunk_contract(
        self, text: str, doc_type: str, source: str, work_id: str | None
    ) -> list[tuple[str, ChunkMetadata]]:
        """
        Contract chunking: align to clause boundaries for legal precision.
        
        Each clause is a natural chunk. Definitions and key terms get special handling.
        """
        metadata = ChunkMetadata(doc_type=doc_type, clause_type="general")

        # Extract clauses
        clause_matches = list(self.CLAUSE_HEADER_RE.finditer(text))
        
        if len(clause_matches) > 1:
            chunks: list[tuple[str, ChunkMetadata]] = []
            
            for i, match in enumerate(clause_matches):
                start = match.start()
                end = clause_matches[i + 1].start() if i + 1 < len(clause_matches) else len(text)
                clause_text = text[start:end].strip()
                
                clause_title = match.group(1).strip()
                clause_type = self._classify_clause(clause_title)
                
                clause_meta = ChunkMetadata(
                    doc_type=doc_type,
                    clause_type=clause_type,
                    work_id=work_id,
                )
                
                # Check for territory/dates in clause
                territories = re.findall(
                    r"\b(Worldwide|United States|North America|Europe|UK|Japan|Territory)\b",
                    clause_text,
                    re.IGNORECASE,
                )
                if territories:
                    clause_meta.territory = territories[0]
                
                header = f"Source: {source}\nClause: {clause_title}\n\n"
                chunks.append((header + clause_text, clause_meta))
            
            # Add preamble chunk
            preamble = text[:clause_matches[0].start()]
            header = f"Source: {source}\nType: Contract / License Agreement\n\n"
            if preamble.strip():
                chunks.insert(0, (header + preamble.strip(), metadata))
            
            return chunks
        else:
            # No clause structure: use paragraph-based chunking
            paragraphs = re.split(r"\n\n+", text)
            paragraphs = [p.strip() for p in paragraphs if len(p.strip()) > 30]
            
            chunks: list[tuple[str, ChunkMetadata]] = []
            current = f"Source: {source}\nType: Contract Document\n\n"
            
            for para in paragraphs:
                if len(current + para) > self.chunk_size:
                    if len(current) >= self.min_chunk_size:
                        chunks.append((current, ChunkMetadata(**metadata.__dict__)))
                    current = f"Source: {source}\nType: Contract Document\n\n" + para
                else:
                    current += "\n\n" + para
            
            if len(current) >= self.min_chunk_size:
                chunks.append((current, ChunkMetadata(**metadata.__dict__)))
            
            return chunks

    def _chunk_generic(
        self, text: str, doc_type: str, source: str, work_id: str | None
    ) -> list[tuple[str, ChunkMetadata]]:
        """Generic chunking with section and paragraph awareness."""
        metadata = ChunkMetadata(doc_type=doc_type)

        # Try to extract work title
        work_match = self.WORK_TITLE_RE.search(text)
        if work_match:
            matched_title = next((g for g in work_match.groups() if g), None)
            metadata.work_title = self._clean_work_title(matched_title)
        elif work_id:
            metadata.work_title = work_id

        # Split on section numbers (e.g. "1. WORK", "2. COMPOSITION") or double newlines
        sections = re.split(r"(?:\n\s*\n+|\s+(?=\d+\.\s+[A-Z\s]{4,}))", text)
        sections = [s.strip() for s in sections if len(s.strip()) > 15]

        if not sections:
            return self._fallback_chunks(text, metadata)

        chunks: list[tuple[str, ChunkMetadata]] = []
        current_parts: list[str] = []
        current_size = 0

        header = f"Source: {source}\nType: {doc_type}\n"
        if metadata.work_title:
            header += f"Work: {metadata.work_title}\n"
        header += "\n"

        for sec in sections:
            if current_size + len(sec) > self.chunk_size and current_parts:
                chunk = header + "\n\n".join(current_parts)
                chunks.append((chunk, ChunkMetadata(**metadata.__dict__)))
                current_parts = []
                current_size = 0
            current_parts.append(sec)
            current_size += len(sec)

        if current_parts:
            chunk = header + "\n\n".join(current_parts)
            chunks.append((chunk, ChunkMetadata(**metadata.__dict__)))

        return chunks if chunks else self._fallback_chunks(text, metadata)

    def _fallback_chunks(self, text: str, metadata: ChunkMetadata) -> list[tuple[str, ChunkMetadata]]:
        """Fallback: split text into fixed-size chunks preserving full text."""
        header = f"Source: {metadata.doc_type}\nType: Document\n\n"
        full_text = header + text
        
        chunks: list[tuple[str, ChunkMetadata]] = []
        step = max(1, self.chunk_size - self.chunk_overlap)
        for i in range(0, len(full_text), step):
            chunk_content = full_text[i:i + self.chunk_size]
            if len(chunk_content.strip()) >= 50:
                chunks.append((chunk_content, ChunkMetadata(**metadata.__dict__)))
        
        if not chunks:
            chunks = [(full_text[:self.chunk_size], ChunkMetadata(**metadata.__dict__))]
        
        return chunks

    def _fallback_chunk(self, text: str, metadata: ChunkMetadata) -> tuple[str, ChunkMetadata]:
        """Legacy helper returning single first chunk."""
        return self._fallback_chunks(text, metadata)[0]

    def validate_splits(self, text: str) -> dict:
        """
        Validate a split sheet document.
        
        Checks:
        - Total shares = 100%
        - All parties have shares
        - Valid percentage formats
        """
        parties = []
        total_share = 0.0
        errors: list[str] = []

        for match in self.PARTY_SHARE_RE.finditer(text):
            name = match.group(1).strip()
            share = float(match.group(2))
            parties.append({"name": name, "share": share})
            total_share += share

        if total_share != 100.0:
            errors.append(f"Total shares: {total_share}% (expected 100%)")

        if len(parties) == 0:
            errors.append("No parties found in document")
        
        return {
            "valid": len(errors) == 0,
            "parties": parties,
            "total_share": total_share,
            "errors": errors,
        }
