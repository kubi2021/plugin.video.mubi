# **White Paper: Refactoring plugin.video.mubi Architecture**

Date: December 13, 2025  
Maintainer: kubi2021  
Repository: github.com/kubi2021/plugin.video.mubi  
Objective: Decouple data retrieval from the Kodi client to improve plugin performance, reduce API pressure, and simplify maintenance.

## **1\. Executive Summary**

The current architecture of plugin.video.mubi relies on a "thick client" approach, where the end-user's device directly queries the Mubi API to resolve regional availability for the entire catalog. While robust against HTML changes, this results in significant latency due to the volume of sequential network requests required to index thousands of films across multiple regions.

The proposed architecture introduces an **Intermediate Data Layer** hosted on GitHub. A scheduled GitHub Action will perform the computational "heavy lifting" (API harvesting, country resolution, metadata fetching) and publish static, versioned, compressed JSON databases. The Kodi plugin will transition to a "thin client," simply downloading these databases to generate the local library instantly.

## **2\. Technical Architecture**

### **2.1 The Data Layer (The "Database")**

We will utilize GitHub's raw file serving capabilities as a high-availability Content Delivery Network (CDN).

* **Format:** JSON, Gzip compressed (.json.gz).  
* **Storage Strategy:** An **orphan branch** (e.g., database or gh-pages) will store the output. This branch will have limited or no history (using force-pushes) to prevent repository bloat.  
* **File Structure:**  
  * **Films:** https://raw.githubusercontent.com/{owner}/{repo}/database/v1/films.json.gz  
  * **Checksums:** https://raw.githubusercontent.com/{owner}/{repo}/database/v1/films.json.gz.md5  
  * **Series:** .../v1/series.json.gz *(Future Implementation)*

  *Note: We will start with a single master `films.json` containing availability for all countries. If file size becomes an issue, we may split into per-country files.*

#### **Data Schema (v1/films.json)**

{  
  "meta": {  
    "generated\_at": "2025-12-13T10:00:00Z",  
    "version": 1,  
    "total\_count": 2150,  
    "hash": "a1b2c3d4..."   
  },  
  "items": \[  
    {  
      "mubi\_id": 12345,  
      "title": "In the Mood for Love",  
      "original\_title": "Fa yeung nin wa",  
      "genres": \["Romance", "Drama"\],  
      "countries": \["US", "GB", "FR", "TR", "IN"\],  
      "tmdb\_id": 843,   
      "imdb\_id": "tt0118694"   
    }  
  \]  
}

### **2.2 The Backend (GitHub Actions)**

The backend logic (scraper and workflows) will reside in a dedicated `backend/` directory within the existing `plugin.video.mubi` repository. This ensures version consistency and simplifies maintenance.

A workflow will run on a schedule (e.g., every 6 hours: 0 \*/6 \* \* \*).

**Workflow Logic:**

1. **Cache Restoration:** Load the films.json database from the *previous* run. This is critical for Phase 3 (metadata enrichment) to avoid re-querying TMDB for movies that haven't changed.  
2. **Data Harvesting:** Query the Mubi API to fetch the global film list and iterate to build the countries list for each film.  
3. **Enrichment:**  
   * Merge new data with cached data.  
   * Fetch missing external IDs (TMDB/IMDB) incrementally to respect rate limits.  
4. **Quality Gate (Integrity Check):**  
   * **Fail Condition:** total\_items \< threshold (e.g., \< 1000). Prevents overwriting a good DB with an empty one if Mubi is down or changes layout.  
   * **Fail Condition:** file\_size \< threshold (e.g., \< 100kb).  
5. **Publish:**  
   * Compress the JSON to films.json.gz.  
   * **Generate Checksum:** Calculate the MD5 hash of the compressed file and save it as films.json.gz.md5.  
   * Force-push both files to the database branch.

### **2.3 The Frontend (Kodi Plugin)**

The plugin logic transitions from an active crawler to a passive consumer.

**New Sync Process (Phase 2):**

1. **Check Update:** Compare local database timestamp/hash with remote.  
2. **Download:** \* Fetch v1/films.json.gz.  
   * Fetch v1/films.json.gz.md5.  
3. **Integrity Check:**  
   * Calculate the MD5 checksum of the downloaded .gz file locally.  
   * Compare it against the content of the downloaded .md5 file.  
   * **Action:** If they do not match, the file is corrupt. Abort the sync and retain the previous library version to prevent data loss.  
4. **Local Processing:**  
   * Decompress in memory.  
   * **Filter:** Check if film countries overlap with user's availability (VPN or physical location).  
   * **Generate:** Create .strm and .nfo files using data directly from the JSON.  
5.  **Fallback & Personalization:**  
    *   **Public Catalog:** Derived exclusively from the JSON.  
    *   **User Data:** Watchlist, Ratings, and "Continue Watching" features will continue to use direct Mubi API calls (authenticated) via the existing plugin logic.  
    *   **Playback:** Stream URLs and DRM keys are fetched on-demand when "Play" is clicked, ensuring freshness. They are NOT stored in the static JSON.

## **3\. Implementation Roadmap**

### **Phase 1: The "Shadow" Backend**

**Goal:** Establish the data pipeline and verify stability without affecting users.

* Develop scraper.py to run in GitHub Actions.  
* Configure the workflow to output films.json.gz and its MD5 to the database orphan branch.  
* Implement "Quality Gates" and error notifications.  
* **Validation:** Run for 1 week to monitor Mubi's response to GitHub IPs and ensure the database is populated correctly.

### **Phase 2: Client Migration**

**Goal:** Switch the plugin to read from the GitHub database.

* Modify plugin.video.mubi to fetch films.json.gz and verify the MD5 checksum.  
* **Transition Strategy:** The "Thick Client" logic will remain as a fallback until the backend is proven stable. Users who do not update will continue to function using the old logic.  
* Plugin relies on the JSON for the film list but still fetches metadata (images/plot) from TMDB locally if needed.

### **Phase 3: Metadata Enrichment**

**Goal:** Move metadata resolution to the server.

* Enhance scraper.py to fetch TMDB/IMDB IDs.  
* Implement caching logic: Only query APIs for *new* Mubi additions.  
* Add tmdb\_id and imdb\_id fields to the JSON schema.

### **Phase 4: Full Decoupling**

**Goal:** Zero-latency syncing.

* Update plugin to rely *exclusively* on the JSON for IDs and metadata.  
* Remove local TMDB querying logic from the sync process.

## **4\. Risk Assessment & Mitigation**

| Risk | Impact | Mitigation Strategy |
| :---- | :---- | :---- |
| **API Blocking** | Mubi blocks GitHub Action IPs or rate-limits requests. | 1\. Implement retry logic with backoff. 2\. Rotate User-Agent headers. 3\. Fallback: Run scraper on external VPS and push to Git. |
| **Data Corruption** | Bad API response pushes empty/corrupt DB, wiping user libraries. | **Strict Quality Gates:** Workflow explicitly fails and aborts the push if the movie count drops significantly (e.g., \>20% drop) compared to the previous run. |
| **Download Corruption** | Incomplete download breaks plugin parsing. | **MD5 Verification:** Plugin validates file integrity using the companion .md5 file before attempting to parse the JSON. |
| **Repo Bloat** | Frequent commits cause .git size to explode. | **Orphan Branch Strategy:** Use git push \--force to a branch with no history. The branch acts as a static file server, not a version history. |
| **API Rate Limits** | TMDB blocks the scraper during Phase 3\. | **Incremental Caching:** Only query metadata for *new* items. Store results in the JSON to prevent re-querying in future runs. |

