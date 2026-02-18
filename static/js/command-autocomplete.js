class CommandAutocomplete {
    constructor(inputElement, inputAreaElement) {
        this.input = inputElement;
        this.inputArea = inputAreaElement;
        this.container = null;
        this.commands = [];
        this.selectedIndex = -1;
        this.isVisible = false;
        this.isLoading = false;
        this.debounceTimer = null;
        this.debounceDelay = 150;
        this.currentQuery = '';
        this.matchType = 'prefix';
        
        this.init();
    }
    
    init() {
        this.container = document.createElement('div');
        this.container.className = 'command-autocomplete';
        this.container.id = 'commandAutocomplete';
        this.inputArea.appendChild(this.container);
        
        this.input.addEventListener('input', this.handleInput.bind(this));
        this.input.addEventListener('keydown', this.handleKeydown.bind(this));
        this.input.addEventListener('blur', this.handleBlur.bind(this));
        this.input.addEventListener('focus', this.handleFocus.bind(this));
        
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target) && e.target !== this.input) {
                this.hide();
            }
        });
    }
    
    handleInput(e) {
        const value = this.input.value;
        const cursorPos = this.input.selectionStart;
        
        const commandMatch = this.extractCommandQuery(value, cursorPos);
        
        if (commandMatch) {
            this.currentQuery = commandMatch.query;
            this.fetchCommandsDebounced(commandMatch.query);
        } else {
            this.hide();
        }
    }
    
    extractCommandQuery(text, cursorPos) {
        const beforeCursor = text.substring(0, cursorPos);
        
        const lines = beforeCursor.split('\n');
        const currentLine = lines[lines.length - 1];
        
        const commandMatch = currentLine.match(/^\/(\w*)$/);
        if (commandMatch) {
            return {
                query: commandMatch[1],
                fullCommand: currentLine
            };
        }
        
        return null;
    }
    
    fetchCommandsDebounced(query) {
        clearTimeout(this.debounceTimer);
        
        this.debounceTimer = setTimeout(() => {
            this.fetchCommands(query);
        }, this.debounceDelay);
    }
    
    async fetchCommands(query) {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading();
        
        try {
            const url = `/api/commands?query=${encodeURIComponent(query)}&match_type=${this.matchType}`;
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success) {
                this.commands = data.commands;
                this.currentQuery = query;
                this.render();
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            console.error('Failed to fetch commands:', error);
            this.showError('Failed to load commands');
        } finally {
            this.isLoading = false;
        }
    }
    
    showLoading() {
        this.container.innerHTML = `
            <div class="command-autocomplete-header">
                <span>Commands</span>
                <span class="match-type">${this.matchType}</span>
            </div>
            <div class="command-autocomplete-loading">Loading commands</div>
        `;
        this.show();
    }
    
    showError(message) {
        this.container.innerHTML = `
            <div class="command-autocomplete-header">
                <span>Commands</span>
                <span class="match-type">Error</span>
            </div>
            <div class="command-autocomplete-empty">
                ${message}
            </div>
        `;
        this.show();
    }
    
    render() {
        if (this.commands.length === 0) {
            this.container.innerHTML = `
                <div class="command-autocomplete-header">
                    <span>Commands</span>
                    <span class="match-type">${this.matchType}</span>
                </div>
                <div class="command-autocomplete-empty">
                    No commands found for "${this.currentQuery}"
                </div>
            `;
            this.show();
            return;
        }
        
        const itemsHtml = this.commands.map((cmd, index) => {
            const highlightedName = this.highlightMatch(cmd.name, this.currentQuery);
            return `
                <div class="command-autocomplete-item${index === this.selectedIndex ? ' selected' : ''}" 
                     data-index="${index}"
                     data-name="${cmd.name}">
                    <div class="command-autocomplete-item-icon">
                        ${cmd.name.charAt(0).toUpperCase()}
                    </div>
                    <div class="command-autocomplete-item-content">
                        <div class="command-autocomplete-item-name">${highlightedName}</div>
                        <div class="command-autocomplete-item-desc">${this.escapeHtml(cmd.description)}</div>
                        <div class="command-autocomplete-item-usage">${this.escapeHtml(cmd.usage)}</div>
                    </div>
                    <div class="command-autocomplete-item-score">${Math.round(cmd.match_score * 100)}%</div>
                </div>
            `;
        }).join('');
        
        this.container.innerHTML = `
            <div class="command-autocomplete-header">
                <span>${this.commands.length} Command${this.commands.length > 1 ? 's' : ''}</span>
                <span class="match-type">${this.matchType}</span>
            </div>
            <div class="command-autocomplete-items">
                ${itemsHtml}
            </div>
            <div class="command-autocomplete-footer">
                <span><kbd>↑</kbd> <kbd>↓</kbd> Navigate</span>
                <span><kbd>Tab</kbd> <kbd>Enter</kbd> Select</span>
                <span><kbd>Esc</kbd> Close</span>
            </div>
        `;
        
        this.attachItemListeners();
        this.show();
    }
    
    highlightMatch(name, query) {
        if (!query) return this.escapeHtml(name);
        
        const escapedName = this.escapeHtml(name);
        const escapedQuery = this.escapeHtml(query);
        
        const regex = new RegExp(`(${this.escapeRegex(escapedQuery)})`, 'gi');
        return escapedName.replace(regex, '<span class="highlight">$1</span>');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    attachItemListeners() {
        const items = this.container.querySelectorAll('.command-autocomplete-item');
        items.forEach(item => {
            item.addEventListener('click', () => {
                const index = parseInt(item.dataset.index);
                this.selectCommand(index);
            });
            
            item.addEventListener('mouseenter', () => {
                this.selectedIndex = parseInt(item.dataset.index);
                this.updateSelection();
            });
        });
    }
    
    handleKeydown(e) {
        if (!this.isVisible) return;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.navigateDown();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.navigateUp();
                break;
            case 'Tab':
            case 'Enter':
                if (this.selectedIndex >= 0) {
                    e.preventDefault();
                    this.selectCommand(this.selectedIndex);
                }
                break;
            case 'Escape':
                e.preventDefault();
                this.hide();
                break;
        }
    }
    
    navigateDown() {
        if (this.commands.length === 0) return;
        this.selectedIndex = (this.selectedIndex + 1) % this.commands.length;
        this.updateSelection();
        this.scrollToSelected();
    }
    
    navigateUp() {
        if (this.commands.length === 0) return;
        this.selectedIndex = this.selectedIndex <= 0 ? this.commands.length - 1 : this.selectedIndex - 1;
        this.updateSelection();
        this.scrollToSelected();
    }
    
    updateSelection() {
        const items = this.container.querySelectorAll('.command-autocomplete-item');
        items.forEach((item, index) => {
            if (index === this.selectedIndex) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }
    
    scrollToSelected() {
        const selectedItem = this.container.querySelector('.command-autocomplete-item.selected');
        if (selectedItem) {
            selectedItem.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
    }
    
    selectCommand(index) {
        if (index < 0 || index >= this.commands.length) return;
        
        const command = this.commands[index];
        const value = this.input.value;
        const cursorPos = this.input.selectionStart;
        
        const beforeCursor = value.substring(0, cursorPos);
        const afterCursor = value.substring(cursorPos);
        
        const newBeforeCursor = beforeCursor.replace(/\/\w*$/, `/${command.name} `);
        
        this.input.value = newBeforeCursor + afterCursor;
        
        const newCursorPos = newBeforeCursor.length;
        this.input.setSelectionRange(newCursorPos, newCursorPos);
        
        this.hide();
        this.input.focus();
    }
    
    handleBlur(e) {
        setTimeout(() => {
            if (!this.container.contains(document.activeElement)) {
                this.hide();
            }
        }, 150);
    }
    
    handleFocus(e) {
        const value = this.input.value;
        const cursorPos = this.input.selectionStart;
        const commandMatch = this.extractCommandQuery(value, cursorPos);
        
        if (commandMatch) {
            this.currentQuery = commandMatch.query;
            this.fetchCommandsDebounced(commandMatch.query);
        }
    }
    
    show() {
        this.container.classList.add('visible');
        this.isVisible = true;
    }
    
    hide() {
        this.container.classList.remove('visible');
        this.isVisible = false;
        this.selectedIndex = -1;
    }
}

window.CommandAutocomplete = CommandAutocomplete;
