"""
Configuration loader for the Flashscore Scraper.
Loads configuration from config.json and provides easy access to settings.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Default configuration
DEFAULT_CONFIG = {
    'browser': {
        'headless': True,
        'window_size': [1920, 1080],
        'disable_images': False
    },
    'timeout': {
        'page_load_timeout': 30,
        'element_timeout': 10,
        'retry_delay': 5,
        'max_retries': 3
    },
    'output': {
        'directory': 'output'
    },
    'logging': {
        'log_level': 'INFO',
        'log_to_file': True,
        'log_file': 'scraper.log',
        # Verbosity flags to reduce noisy debug logs
        'verbose_odds_debug': False,
        'verbose_url_builder_debug': False
    },
    'batch': {
        'base_batch_size': 2,
        'base_delay': 3.0,
        'adaptive_delay': True
    },
    'scraping': {
        'max_matches': 3,
        'min_h2h_matches': 6
    },
    'selectors': {
        # Add default selectors here from config.json
    }
}

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from a JSON file or use defaults.
    
    Args:
        config_path: Path to the config file. If None, looks for 'src/config.json'.
        
    Returns:
        dict: Loaded configuration
    """
    if config_path is None:
        config_path = os.path.join('src', 'config.json')
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge with defaults to ensure all required keys exist
                merged_config = _deep_merge(DEFAULT_CONFIG, config)
                # Validate selectors and add defaults for missing ones
                return validate_selectors(merged_config)
    except Exception as e:
        print(f"Warning: Could not load config from {config_path}: {e}")
    
    # Return validated default config
    return validate_selectors(DEFAULT_CONFIG.copy())

def save_config(config: Dict[str, Any], config_path: str = None) -> bool:
    """
    Save configuration to a JSON file.
    
    Args:
        config: Configuration dictionary to save
        config_path: Path to save the config file. If None, uses 'src/config.json'.
        
    Returns:
        bool: True if successful, False otherwise
    """
    if config_path is None:
        config_path = os.path.join('src', 'config.json')
    
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config to {config_path}: {e}")
        return False

def _deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two dictionaries.
    
    Args:
        base: Base dictionary to update
        update: Dictionary with updates to apply
        
    Returns:
        dict: Merged dictionary
    """
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def validate_selectors(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that required selectors are present in the configuration.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        dict: Validated configuration with defaults for missing selectors
    """
    required_selectors = {
        'match': {
            'scheduled': 'div.event__match--scheduled',
            'teams': {
                'home': 'div.duelParticipant__home .participant__participantName',
                'away': 'div.duelParticipant__away .participant__participantName'
            },
            'datetime': {
                'container': 'div.duelParticipant__startTime'
            },
            'navigation': {
                'text': 'span[data-testid="wcl-scores-overline-03"]',
                'country': {'index': 1},
                'league': {'index': 2}
            }
        },
        'odds': {
            'table': {
                'home_away': {
                    'odds': {
                        'home': {'cell': '.oddsTab__tableWrapper .ui-table__row a.oddsCell__odd:nth-of-type(1)'},
                        'away': {'cell': '.oddsTab__tableWrapper .ui-table__row a.oddsCell__odd:nth-of-type(2)'}
                    }
                },
                'over_under': {
                    'odds': {
                        'total': {'cell': '.oddsTab__tableWrapper .ui-table__row .wcl-oddsCell span[data-testid="wcl-oddsValue"]'},
                        'over': {'cell': '.oddsTab__tableWrapper .ui-table__row a.oddsCell__odd:nth-of-type(1) span'},
                        'under': {'cell': '.oddsTab__tableWrapper .ui-table__row a.oddsCell__odd:nth-of-type(2) span'}
                    }
                }
            }
        },
        'h2h': {
            'section': 'div.h2h__section',
            'row': 'a.h2h__row',
            'date': 'span.h2h__date',
            'no_data': 'div.noData.noData--npb',
            'home_participant': {
                'container': 'span.h2h__participant.h2h__homeParticipant'
            },
            'away_participant': {
                'container': 'span.h2h__participant.h2h__awayParticipant'
            },
            'result': {
                'container': 'div.h2h__result',
                'home': 'div.h2h__result span:nth-child(1)',
                'away': 'div.h2h__result span:nth-child(2)'
            },
            'event': {'container': 'span.h2h__event'},
            'show_more': 'button[data-testid="wcl-buttonLink"], button.wclButtonLink--h2h'
        }
    }
    
    # Ensure selectors section exists
    if 'selectors' not in config:
        config['selectors'] = {}
    
    # Merge required selectors with existing ones
    config['selectors'] = _deep_merge(required_selectors, config.get('selectors', {}))
    
    return config

# Global configuration instance
CONFIG = load_config()

# Common constants
DEFAULT_OUTPUT_FILE = 'matches.csv'

# Minimum number of H2H matches required
MIN_H2H_MATCHES = 6

# Note: All URL generation is now handled by the UrlBuilder class
from src.core.url_builder import UrlBuilder

# For backward compatibility
SELECTORS = CONFIG.get('selectors', {})
