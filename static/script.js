document.addEventListener('DOMContentLoaded', () => {
    const searchButton = document.getElementById('search-button');
    const searchInput = document.getElementById('search-input');
    const resultsSection = document.getElementById('results-section');

    // Add event listener for Enter key in search input
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    // Add click event listener to search button
    searchButton.addEventListener('click', performSearch);

    // Main search function
    async function performSearch() {
        const query = searchInput.value.trim();
        if (!query) {
            showError('Please enter a search query.');
            return;
        }

        showLoading();

        try {
            const response = await fetch('/api/v1/explain-news-by-query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ search_query: query }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            displayResults(data);

        } catch (error) {
            showError(`Error: ${error.message}`);
            console.error('Search error:', error);
        }
    }

    // Display loading state
    function showLoading() {
        resultsSection.innerHTML = `
            <div class="loading">
                <div class="loading-spinner"></div>
                <p>Searching for information...</p>
            </div>
        `;
    }

    // Display error message
    function showError(message) {
        resultsSection.innerHTML = `
            <div class="error-message">
                <p>${message}</p>
            </div>
            <p>Please try a different search query or try again later.</p>
        `;
    }

    // Display search results
    function displayResults(data) {
        // Start with the summary section
        let html = `
            <div class="summary-highlight">
                <h2>Summary</h2>
                <p>${data.summary || 'No summary available.'}</p>
            </div>
        `;
        
        // Add full explanation if available
        if (data.full_explanation) {
            html += `
                <h2>Full Explanation</h2>
                <div class="full-explanation">
                    <p>${formatContent(data.full_explanation)}</p>
                </div>
            `;
        }

        // Add citations if available
        if (data.citations && data.citations.length > 0) {
            html += '<h2>Citations</h2>';
            
            // Use citation cards instead of a simple list
            data.citations.forEach(citation => {
                html += `
                    <div class="citation-card">
                        <div class="citation-source">
                            ${citation.source_url 
                                ? `<a href="${citation.source_url}" target="_blank">${citation.source_name || 'Source'}</a>`
                                : citation.source_name || 'Source'
                            }
                        </div>
                        ${citation.snippet 
                            ? `<div class="citation-snippet">${citation.snippet}</div>`
                            : ''
                        }
                    </div>
                `;
            });
        }

        // Add related topics if available
        if (data.related_topics && data.related_topics.length > 0) {
            html += '<h2>Related Topics</h2><div class="related-topics">';
            data.related_topics.forEach(topic => {
                html += `<span class="topic-tag">${topic}</span>`;
            });
            html += '</div>';
        }

        // Add a search again prompt
        html += `
            <div class="search-again">
                <p>Not what you're looking for? <button id="new-search-button">Try another search</button></p>
            </div>
        `;
        
        resultsSection.innerHTML = html;
        
        // Add event listener to the "new search" button
        const newSearchButton = document.getElementById('new-search-button');
        if (newSearchButton) {
            newSearchButton.addEventListener('click', () => {
                searchInput.focus();
                searchInput.select();
            });
        }
    }

    // Helper function to format content with paragraphs
    function formatContent(content) {
        // Split by double newlines to create paragraphs
        const paragraphs = content.split(/\n\n+/);
        return paragraphs.map(p => `<p>${p.trim()}</p>`).join('');
    }
});
