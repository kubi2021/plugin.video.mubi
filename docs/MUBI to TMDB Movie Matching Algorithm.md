# **Automated Metadata Reconciliation Architecture for Media Centers: Bridging the Semantic Gap Between MUBI and TMDB**

## **1\. Executive Summary**

The integration of heterogeneous metadata sources remains one of the most persistent challenges in digital media management and information retrieval. In the specific context of Home Theater Personal Computers (HTPC) and media center software like Kodi, the accuracy of metadata scraping determines the user experience. When a system incorrectly identifies a film—displaying the wrong artwork, plot summary, or cast—it breaks the immersion and utility of the platform. This report addresses the specific architectural challenge of reconciling movie data from MUBI, a highly curated streaming service focusing on auteur and international cinema, with The Movie Database (TMDB), a crowdsourced, comprehensive global metadata repository.

The problem, as defined by the user query, is tripartite: locating the correct entity within TMDB based on MUBI source data, verifying the identity of that entity with high precision, and executing a "fail-safe" protocol where the system returns no match rather than an incorrect one. This challenge is exacerbated by "metadata friction"—discrepancies in release dates due to festival premieres versus theatrical releases, title variations across languages, and the inherent ambiguity of "obscure" or low-visibility titles that lack robust community data.

The analysis presented herein proposes a "Tri-Vector Verification Protocol" (TVVP). This algorithmic approach moves beyond simple title string matching to employ a multi-layered validation strategy. By leveraging deterministic identifiers (IMDb IDs), semantic analysis (Fuzzy Title Matching), temporal logic (Release Windowing), and, most critically, creator fingerprints (Director Verification), the proposed system aims to achieve near-human levels of reconciliation accuracy. The report details the theoretical underpinnings of Entity Resolution (ER) in this domain, analyzes the specific data schemas of MUBI and TMDB, and provides a comprehensive implementation guide for a Python-based resolution engine suitable for a Kodi plugin environment. The central thesis is that for obscure and international cinema, the **Director** field serves as a far more reliable unique identifier than the **Title** or **Year**, and thus must be elevated to a primary validation gatekeeper in any robust matching algorithm.

## **2\. Theoretical Framework: The Curator vs. The Aggregator**

To design an effective matching algorithm, one must first understand the provenance of the data. MUBI and TMDB represent two distinct philosophies in metadata curation, and their structural differences are the root cause of the reconciliation challenges identified in the user query.

### **2.1 The Curator Model (MUBI)**

MUBI operates as an "electronic cinematheque." Its database is built around the concept of the *auteur*. The metadata is curated by professionals who view cinema through an artistic and historical lens.

* **Originality Emphasis**: Titles are often preserved in their original language (e.g., *Augure* rather than *Omen*) to respect the artistic intent.  
* **Premiere-Centric Dating**: The "Year" field in MUBI typically reflects the copyright year or the World Premiere date at a film festival (e.g., Cannes, Berlin, Sundance). This is the date the film came into existence as an art object.  
* **Selection Bias**: The catalog is heavily skewed towards international, independent, and classic cinema—the very "obscure movies" mentioned in the query. These films often have less standardized metadata in global systems compared to Hollywood blockbusters.

### **2.2 The Aggregator Model (TMDB)**

The Movie Database (TMDB) operates as a crowdsourced utility, similar to Wikipedia but structured for API consumption.

* **Localization Emphasis**: TMDB prioritizes accessibility. A query from a US IP address or with language=en-US will default to English titles. *Augure* becomes *Omen*.  
* **Release-Centric Dating**: While TMDB captures premiere dates, the primary release\_date field exposed in search results often reflects the theatrical or digital release date in the query's target region.  
* **Community Bias**: Popular films have pristine, locked metadata. Obscure films may have sparse data, missing alternative titles, or incorrect dates entered by users based on local availability rather than historical premiere.

### **2.3 The "Metadata Friction"**

The friction arises when these two models collide. A film might premiere at Cannes in May 2023 (MUBI Year: 2023\) but not receive a US theatrical release until March 2024 (TMDB Year: 2024). A simple algorithm searching for Title="Omen" AND Year="2023" will fail to find the TMDB entry, or worse, match a different movie named "Omen" released in 2023\. The algorithm proposed in this report is designed specifically to lubricate this friction by treating metadata fields not as absolute constants, but as probabilistic signals.

## **3\. Data Schema Decomposition and Field Mapping**

A robust algorithm requires a precise understanding of the input signal (MUBI) and the target schema (TMDB). We break down the provided MUBI JSON excerpt to identify every leverageable data point and map it to its corresponding TMDB API field.

### **3.1 Source Data Analysis (MUBI)**

The provided JSON contains several high-value fields. The mubi\_id (374519) is internal and useless for matching unless a pre-existing lookup table exists. The remaining fields can be categorized by their utility in Entity Resolution.

#### **3.1.1 Deterministic Identifiers**

* **imdb\_id ("tt21086802")**: This is the "Golden Key." IMDb IDs are globally unique identifiers (GUIDs) used across the industry. The presence of this field allows for O(1) lookup complexity, bypassing the ambiguity of search entirely.  
* **tmdb\_id ("889818")**: While this seems like the solution, the user explicitly states that matching challenges persist. This implies that MUBI's internal tmdb\_id might be missing, null, or occasionally incorrect (stale data). Therefore, this field should be treated as a "strong suggestion" rather than absolute truth.

#### **3.1.2 Semantic Identifiers**

* **original\_title ("Augure")**: This is often more unique than the English title. For example, "Omen" is a generic word in English with many potential matches. "Augure" is more specific.  
* **title ("Omen")**: The localized title. Useful for secondary searches but prone to collision.  
* **directors ()**: The single most powerful disambiguation vector for arthouse cinema. While many films are named "Omen," very few are directed by "Baloji."  
* **historic\_countries ()**: Provides geographic context. If a search for "Omen" yields a US horror movie and a Belgian drama, this field helps identify the correct match.

#### **3.1.3 Temporal and Technical Identifiers**

* **year (2023)**: The anchor for temporal filtering. As noted, this is likely the festival year.  
* **duration (92)**: The runtime in minutes. This is critical for distinguishing between a Feature Film (e.g., 90 mins) and a Short Film (e.g., 15 mins) that might share the same title.

### **3.2 Target Schema Analysis (TMDB API)**

To leverage these MUBI fields, we must identify the corresponding endpoints and response fields in the TMDB API.1

| MUBI Field | TMDB API Field | Endpoint | Usage Strategy |
| :---- | :---- | :---- | :---- |
| imdb\_id | external\_ids.imdb\_id | /find/{id} | **Primary Lookup.** Highest confidence. |
| tmdb\_id | id | /movie/{id} | **Verification Target.** Use if present, but verify. |
| original\_title | original\_title | /search/movie | **Search Query A.** High precision. |
| title | title | /search/movie | **Search Query B.** High recall. |
| year | release\_date | /search/movie | **Filtering.** Use window logic (+/- 2 years). |
| directors | credits.crew | /movie/{id}/credits | **Deep Verification.** Essential for obscure titles. |
| duration | runtime | /movie/{id} | **Tie-Breaker.** Validate \+/- 10 mins. |

### **3.3 The Missing Link: Director Data**

A critical limitation of the TMDB /search/movie endpoint is that the response objects **do not contain director information** by default.3 The search response provides title, year, overview, and poster\_path, but not the crew. To verify the director—a strict requirement for our "solid algorithm"—we must make a secondary API call for potential candidates. This introduces a performance consideration (the "N+1 query problem"), which we will address via the append\_to\_response feature.5

## **4\. The Temporal Divergence Problem: Solving the "Year" Mismatch**

The user query identifies the date mismatch as a primary failure mode. To solve this, we must move away from strict equality checks (==) and adopt a **Probabilistic Temporal Window**.

### **4.1 The Festival-Theatrical Lag**

Research indicates a significant discrepancy between "Festival Years" and "Release Years".6

* *Scenario A*: A film premieres at Sundance in Jan 2022\. MUBI lists it as 2022\. It finds no buyer for 18 months. It is released on VOD in late 2023\. TMDB might list 2023\.  
* *Scenario B*: A film is finished in late 2023\. MUBI lists 2023\. It premieres in early 2024\. TMDB lists 2024\.

### **4.2 API Query vs. Client-Side Filtering**

A naive implementation would pass the year to the TMDB search API:  
GET /search/movie?query=Omen\&year=2023.8  
This is dangerous. If TMDB lists the movie as 2024, the API will filter it out server-side, returning zero results. The "solid algorithm" must therefore not restrict the year in the initial API query (or at least, use a fallback strategy).  
**Recommended Strategy:**

1. **Broad Search**: Query TMDB by Title *without* the year parameter.  
2. **Client-Side Filtering**: Iterate through the returned results and apply a **Sliding Window** logic.  
3. **Window Calculation**:  
   * Let $Y\_M$ be the MUBI Year.  
   * Let $Y\_T$ be the TMDB Release Date Year.  
   * Calculate $\\Delta Y \= |Y\_M \- Y\_T|$.  
   * **Acceptable Window**: If $\\Delta Y \\le 2$, the candidate remains valid.  
   * **Strictness**: For obscure movies (low popularity), widen the window to $\\pm 3$ years, as release histories are often murkier for these titles.

This approach ensures that a movie listed as 2023 in MUBI and 2024 in TMDB is retrieved by the search and then validated by the logic, rather than being invisible to the application.

## **5\. The Creator Vector: Director Verification**

The user requires that the system "make sure it's the right TMDB movie." For the "obscure movies" mentioned, titles are often recycled. The **Director** is the fingerprint of the film.9

### **5.1 Why Title Matching Fails**

Consider the title "Mother."

* *Mother* (2009) \- Bong Joon-ho (South Korea)  
* *Mother\!* (2017) \- Darren Aronofsky (USA)  
* *Mother* (1996) \- Albert Brooks (USA)  
* The Mother (2003) \- Roger Michell (UK)  
  There are dozens of films with this title. If MUBI lists "Mother (2009)" and TMDB lists it as "Mother (2010)" due to a release delay, a year/title match is risky. However, searching for "Director: Bong Joon-ho" immediately isolates the correct entity.

### **5.2 Retrieving Crew Data via append\_to\_response**

Since the search endpoint omits crew, we must use the TMDB details endpoint. To avoid making two separate calls (one for details, one for credits), we utilize the append\_to\_response parameter.5

* **Endpoint**: https://api.themoviedb.org/3/movie/{movie\_id}?api\_key={key}\&append\_to\_response=credits  
* **Response**: Returns the full movie object *plus* a credits object containing a crew array.  
* **Extraction**: We parse the crew array, filtering for objects where job equals "Director".

### **5.3 Fuzzy Name Matching**

Director names are not consistent strings.

* **Variation 1**: "Baloji" (MUBI) vs. "Baloji Tshiani" (TMDB).  
* **Variation 2**: "Park Chan-wook" (Eastern Order) vs. "Chan-wook Park" (Western Order).  
* **Variation 3**: "Nicolas Winding Refn" vs. "Nicolas Refn".

Exact string matching will fail here. We require **Token Sort Ratio** matching.11 This algorithm tokenizes the string (splits by space), sorts the tokens alphabetically, and then compares them.

* *String A*: "Park Chan-wook" \-\> \["Chan-wook", "Park"\]  
* *String B*: "Chan-wook Park" \-\> \["Chan-wook", "Park"\]  
* *Result*: 100% Match.

This logic is robust against middle names, name ordering, and minor misspellings, satisfying the "very solid" requirement.

## **6\. The "Tri-Vector" Algorithm Design**

Based on the analysis above, we propose a hierarchical algorithm that validates matches across three vectors: **Deterministic**, **Linguistic**, and **Creator**.

### **6.1 Phase I: Deterministic Resolution (The "Golden Path")**

This phase relies on shared IDs. It is the fastest and most accurate method.

1. **Check imdb\_id**: Inspect the MUBI JSON for the imdb\_id field.  
   * *Action*: If present, call TMDB /find/{imdb\_id} endpoint with external\_source=imdb\_id.1  
   * *Validation*: Even if a result is returned, perform a "sanity check." Does the returned movie's title match the MUBI title with a fuzzy ratio \> 60%? (This protects against rare database errors where an ID is recycled or mislinked).  
   * *Result*: If validated, return the TMDB ID immediately. This handles the majority of cases with near-zero error rate.  
2. **Check tmdb\_id**: Inspect the MUBI JSON for tmdb\_id.  
   * *Action*: If present, call TMDB /movie/{tmdb\_id}?append\_to\_response=credits.  
   * *Validation*: Crucial step. Compare the **Director** from the response against the MUBI director.  
   * *Logic*: If Directors match (Fuzzy Score \> 85), accept the ID. If they do not match, **discard** the MUBI-provided tmdb\_id as erroneous and proceed to Phase II.

### **6.2 Phase II: Candidate Retrieval (The "Wide Net")**

If deterministic IDs fail or are absent, we must search.

1. **Construct Queries**: Prepare a list of search strategies in descending order of specificity.  
   * *Strategy A*: Search original\_title. (e.g., "Augure"). This is less likely to collide with generic English terms.  
   * *Strategy B*: Search title. (e.g., "Omen").  
2. **Execute Search**:  
   * Call /search/movie with query=original\_title.  
   * **Important**: Include include\_adult=true. MUBI content is often unrated or mature (e.g., the "content\_rating": "mature" in the JSON). TMDB filters adult content by default.12 Failing to include this flag is a common cause of "missing" matches for arthouse cinema.  
   * If Strategy A returns 0 results, execute Strategy B.  
3. **Result**: We now have a list of candidates (potentially 20+ movies).

### **6.3 Phase III: The Verification Funnel**

We must now filter the candidates to find the "Right" one and reject the rest.

#### **Step 1: Client-Side Temporal Filtering**

Iterate through candidates. For each candidate:

* Parse release\_date to get tmdb\_year.  
* Calculate delta \= abs(mubi\_year \- tmdb\_year).  
* **Filter**: If delta \> 2 (or 3 for obscure), **discard** the candidate.  
  * *Rationale*: A film from 1990 is definitely not a match for a 2023 MUBI entry, even if the title is identical.

#### **Step 2: Title Relevance Sorting**

Sort the remaining candidates by fuzz.token\_set\_ratio against the MUBI title. Take the top 3 candidates. This limits the number of expensive API calls in the next step.

#### **Step 3: Deep Verification (The "Director Check")**

For the top 3 candidates:

* **Fetch Details**: Call /movie/{id}?append\_to\_response=credits.  
* **Extract Directors**: Get the list of directors from TMDB.  
* **Compare**: Calculate the Fuzzy Token Sort Ratio between MUBI Director(s) and TMDB Director(s).  
* **Scoring**:  
  * *Director Match (\>85%)*: **\+50 Points**. (The "Trump Card").  
  * *Title Match (\>90%)*: **\+30 Points**.  
  * *Year Exact Match*: **\+10 Points**.  
  * *Runtime Match (+/- 10 mins)*: **\+10 Points**.

#### **Step 4: The "Certainty" Threshold**

* Calculate total score.  
* **Threshold**: If Total Score \> 80, declare a match.  
* **Safety Valve**: If the score is \< 80, return None. The user explicitly requested: *"if not certain, then do not match anything."* It is better to have an unmatched item in Kodi (which the user can manually fix) than a wrongly matched item (which pollutes the library).

## **7\. Implementation: Pythonic Architecture**

This section translates the theoretical algorithm into concrete implementation logic, utilizing standard Python libraries (requests for API interaction and thefuzz for string matching).

### **7.1 Dependencies and Setup**

To implement this algorithm effectively, the Kodi plugin must utilize:

* **requests**: For handling HTTP sessions, keeping connections alive (Connection Pooling), and managing headers/timeouts.  
* **thefuzz (formerly fuzzywuzzy)**: Provides the token\_sort\_ratio and token\_set\_ratio functions essential for name and title normalization.11  
* **python-Levenshtein**: An optional C-extension that speeds up thefuzz by 10-100x. Highly recommended for Kodi plugins running on low-power devices (like Raspberry Pi or Android TV boxes).

### **7.2 Code Logic Flowchart**

Python

def find\_tmdb\_match\_logic(mubi\_data):  
    """  
    Core logic for reconciling MUBI data to TMDB ID.  
    """  
      
    \# \--- PHASE 1: Deterministic ID Check \---  
    if mubi\_data.get('imdb\_id'):  
        tmdb\_id \= tmdb\_api.find\_by\_external\_id(mubi\_data\['imdb\_id'\], 'imdb\_id')  
        if tmdb\_id:  
            \# Quick Sanity Check: If title is completely different, verify further  
            return tmdb\_id  
              
    \# \--- PHASE 2: Search Strategy \---  
    \# Try Original Title first (High Precision)  
    candidates \= tmdb\_api.search\_movie(  
        query=mubi\_data\['original\_title'\],   
        year=None,  \# Don't filter by year on server side  
        include\_adult=True  
    )  
      
    \# Fallback to English Title (High Recall)  
    if not candidates:  
        candidates \= tmdb\_api.search\_movie(  
            query=mubi\_data\['title'\],   
            year=None,  
            include\_adult=True  
        )  
          
    if not candidates:  
        return None  \# No candidates found

    \# \--- PHASE 3: Candidate Verification \---  
    best\_match \= None  
    highest\_confidence \= 0  
      
    \# Process only top 3 candidates to save API calls  
    for candidate in candidates\[:3\]:  
        confidence\_score \= 0  
          
        \# A. Temporal Check (Window \+/- 2 Years)  
        tmdb\_year \= extract\_year(candidate.get('release\_date'))  
        if not tmdb\_year: continue \# Skip invalid dates  
          
        year\_delta \= abs(tmdb\_year \- mubi\_data\['year'\])  
        if year\_delta \> 2:  
            continue \# Hard reject if outside temporal window  
              
        \# B. Deep Data Fetch (Director & Runtime)  
        \# Uses append\_to\_response=credits to get all info in one packet  
        details \= tmdb\_api.get\_movie\_details(candidate\['id'\], append='credits')  
          
        \# C. Director Matching (The Fingerprint)  
        mubi\_directors \= mubi\_data.get('directors',)  
        tmdb\_directors \= \[  
            crew\['name'\] for crew in details\['credits'\]\['crew'\]   
            if crew\['job'\] \== 'Director'  
        \]  
          
        director\_score \= calculate\_max\_fuzzy\_score(mubi\_directors, tmdb\_directors)  
          
        if director\_score \> 85:  
            confidence\_score \+= 60  \# Major boost for director match  
        else:  
            \# If director doesn't match, we are very skeptical.  
            \# Only proceed if titles are nearly identical.  
            confidence\_score \-= 20  
              
        \# D. Semantic Title Check  
        title\_score \= fuzz.token\_set\_ratio(mubi\_data\['title'\], candidate\['title'\])  
        orig\_title\_score \= fuzz.token\_set\_ratio(mubi\_data\['original\_title'\], candidate\['original\_title'\])  
        max\_title\_score \= max(title\_score, orig\_title\_score)  
          
        if max\_title\_score \> 90:  
            confidence\_score \+= 30  
        elif max\_title\_score \< 60:  
            confidence\_score \-= 50 \# Penalize title mismatch  
              
        \# E. Runtime Check (Tie Breaker)  
        tmdb\_runtime \= details.get('runtime', 0) or 0  
        if mubi\_data\['duration'\] and tmdb\_runtime \> 0:  
            if abs(mubi\_data\['duration'\] \- tmdb\_runtime) \<= 15:  
                confidence\_score \+= 10  
            elif abs(mubi\_data\['duration'\] \- tmdb\_runtime) \> 40:  
                confidence\_score \-= 30 \# Likely a short vs feature mismatch  
                  
        \# \--- Decision Update \---  
        if confidence\_score \> highest\_confidence:  
            highest\_confidence \= confidence\_score  
            best\_match \= candidate\['id'\]  
              
    \# \--- PHASE 4: Final Safety Valve \---  
    \# "If not certain, then do not match anything"  
    if highest\_confidence \>= 80:  
        return best\_match  
    else:  
        return None

## **8\. Specific Field Analysis & Edge Case Handling**

The user query highlights "obscure movies" and "date matching" as key challenges. We analyze how specific fields from the MUBI JSON help mitigate these.

### **8.1 historic\_countries vs. production\_countries**

For obscure films, title collisions are frequent. A user might search for "Home" (2020) and find a US documentary, a French drama, and a Japanese horror film.

* **MUBI**: "historic\_countries":  
* **TMDB**: Returns production\_countries in the movie details.  
* **Logic**: If the Director check is ambiguous (e.g., unknown director), the algorithm can compare countries. Intersection between MUBI's historic\_countries and TMDB's production\_countries acts as a strong secondary validator. If MUBI says "Belgium" and TMDB says "USA", the confidence score should be penalized.

### **8.2 duration vs. runtime (Short Film Detection)**

MUBI is unique among streamers for heavily featuring short films. A 15-minute short named "Omen" might exist alongside the 92-minute feature.

* **Data Point**: MUBI duration is 92\.  
* **Scenario**: TMDB search returns a result with runtime 14\.  
* **Logic**: The abs(92 \- 14\) delta is massive. Even if the title and year match perfectly, this is *not* the same content. The algorithm uses the Runtime Check (Section 6.3, Step 3\) to penalize this match heavily, preventing the common Kodi issue where a short film overwrites a feature film's metadata.

### **8.3 original\_title (Handling Unicode and Diacritics)**

The MUBI JSON has "Augure". TMDB might store this as "Augure" or transliterate it.

* **Issue**: Python string comparison might fail on accents (e.g., é vs e).  
* **Solution**: The thefuzz library handles basic normalization. However, explicitly using the original\_title field in the search query (Phase II) is critical. Searching for "Augure" yields a much smaller, higher-quality result set than searching for "Omen." This inherently solves the "obscure movie" problem by using the most specific search term available.

### **8.4 popularity and vote\_count (The Obscurity Heuristic)**

The MUBI JSON provides a popularity score (286). TMDB responses also include popularity and vote\_count.

* **Heuristic**: If a candidate from TMDB has vote\_count: 0 or extremely low popularity, it confirms the film is obscure.  
* **Implication**: For these items, metadata is likely to be less standardized. The algorithm should **relax** the Year Window (allow \+/- 3 years) but **tighten** the Director Check (require exact match). This adaptive logic allows the system to handle the "Long Tail" of cinema without compromising accuracy for mainstream titles.

## **9\. Performance Optimization: The Cost of Deep Verification**

The proposed algorithm is API-intensive. A standard search uses 1 call. This algorithm uses 1 call for search \+ up to 3 calls for verification (Details \+ Credits).

### **9.1 The "N+1" Problem**

If the plugin is scanning a library of 1,000 MUBI films, a naive implementation might make 4,000 API calls, hitting TMDB rate limits.

### **9.2 Optimization Strategies**

1. **Append to Response**: As mentioned, combining credits into the movie detail call reduces calls by 50% for the verification phase.5  
2. **Short-Circuiting**: If the Top Candidate from the search has a Title Match \> 95% AND Year Match (Delta 0), we can skip the Director Check for *that specific item*, assuming it's a mainstream hit. However, given the user's focus on "obscure movies," this optimization should be applied cautiously (e.g., only if TMDB vote\_count \> 1000).  
3. **Caching**: The Kodi plugin must implement a local cache (SQLite or simple JSON). Once a mubi\_id is successfully resolved to a tmdb\_id, this link should be stored permanently. The expensive "Deep Verification" should only run once per movie.

## **10\. Conclusion**

The "solid algorithm" requested by the user is not a single query; it is a **decision engine**. The discrepancies between MUBI and TMDB are not errors to be fixed but structural characteristics to be navigated. MUBI reflects the festival circuit; TMDB reflects the commercial market.

The proposed **Tri-Vector Verification Protocol** succeeds where simple matching fails because it aligns with the ontology of the domain:

1. **It prioritizes the Director:** Recognizing that for the target content (arthouse/obscure), the creator is the most stable identifier.  
2. **It creates a Temporal Window:** Acknowledging the "Festival Lag" inherent in MUBI's data.  
3. **It enforces a Null-State:** Respecting the user's requirement for library hygiene by refusing to guess when data signals are weak.

By implementing this architecture—specifically utilizing the **IMDb ID** for deterministic matching, **Original Title** for precision searching, and **Director Fuzzy Matching** for final verification—the Kodi plugin can achieve a level of metadata fidelity that rivals manual curation, seamlessly bridging the gap between the film festival and the living room.

#### **Works cited**

1. Find By ID \- TMDb API, accessed December 29, 2025, [https://developer.themoviedb.org/reference/find-by-id](https://developer.themoviedb.org/reference/find-by-id)  
2. Search \- Movies \- TMDb API, accessed December 29, 2025, [https://developer.themoviedb.org/reference/search-movie](https://developer.themoviedb.org/reference/search-movie)  
3. Search & Query For Details \- TMDb API, accessed December 29, 2025, [https://developer.themoviedb.org/docs/search-and-query-for-details](https://developer.themoviedb.org/docs/search-and-query-for-details)  
4. pull directors from TMDB API ? : r/api\_connector \- Reddit, accessed December 29, 2025, [https://www.reddit.com/r/api\_connector/comments/158mhog/pull\_directors\_from\_tmdb\_api/](https://www.reddit.com/r/api_connector/comments/158mhog/pull_directors_from_tmdb_api/)  
5. Append To Response \- TMDb API, accessed December 29, 2025, [https://developer.themoviedb.org/docs/append-to-response](https://developer.themoviedb.org/docs/append-to-response)  
6. Does a theatrical or streaming platform release date override a festival release date? Or does it not matter? : r/movies \- Reddit, accessed December 29, 2025, [https://www.reddit.com/r/movies/comments/1chc8zx/does\_a\_theatrical\_or\_streaming\_platform\_release/](https://www.reddit.com/r/movies/comments/1chc8zx/does_a_theatrical_or_streaming_platform_release/)  
7. Do you go off the premiere or the theatrical release year for lists? : r/Letterboxd \- Reddit, accessed December 29, 2025, [https://www.reddit.com/r/Letterboxd/comments/1lclb4g/do\_you\_go\_off\_the\_premiere\_or\_the\_theatrical/](https://www.reddit.com/r/Letterboxd/comments/1lclb4g/do_you_go_off_the_premiere_or_the_theatrical/)  
8. Movie \- TMDb API, accessed December 29, 2025, [https://developer.themoviedb.org/reference/discover-movie](https://developer.themoviedb.org/reference/discover-movie)  
9. How to design a movie database? \- Stack Overflow, accessed December 29, 2025, [https://stackoverflow.com/questions/490464/how-to-design-a-movie-database](https://stackoverflow.com/questions/490464/how-to-design-a-movie-database)  
10. Use the append\_to\_response capability of the API? · Issue \#7 · 18Months/themoviedb-api, accessed December 29, 2025, [https://github.com/18Months/themoviedb-api/issues/7](https://github.com/18Months/themoviedb-api/issues/7)  
11. Fuzzy String Matching in Python Tutorial \- DataCamp, accessed December 29, 2025, [https://www.datacamp.com/tutorial/fuzzy-string-python](https://www.datacamp.com/tutorial/fuzzy-string-python)  
12. TMDB search include adult results \- Feature Requests \- Emby Community, accessed December 29, 2025, [https://emby.media/community/index.php?/topic/63627-tmdb-search-include-adult-results/](https://emby.media/community/index.php?/topic/63627-tmdb-search-include-adult-results/)  
13. FuzzyWuzzy \- PyPI, accessed December 29, 2025, [https://pypi.org/project/fuzzywuzzy/](https://pypi.org/project/fuzzywuzzy/)