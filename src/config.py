"""Configuration settings for the Flashscore scraper."""
import os
import json
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class BrowserConfig:
    """Browser-specific configuration."""
    browser_name: str = "chrome"  # 'chrome' or 'firefox'
    headless: bool = True
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    window_size: tuple[int, int] = (1920, 1080)
    download_path: Optional[str] = None
    proxy: Optional[str] = None
    ignore_certificate_errors: bool = False
    disable_images: bool = True
    disable_javascript: bool = False
    disable_css: bool = False
    driver_path: Optional[str] = None  # Path to ChromeDriver or GeckoDriver executable
    chrome_binary_path: Optional[str] = None  # Path to Chrome browser binary
    chromedriver_path: Optional[str] = None  # Path to ChromeDriver executable

@dataclass
class TabConfig:
    """Tab management configuration."""
    max_tabs: int = 1
    min_load_interval: float = 2.0
    tab_recovery_attempts: int = 3
    tab_health_check_interval: float = 5.0
    tab_cleanup_interval: float = 300.0  # 5 minutes
    max_tab_age: float = 3600.0  # 1 hour

@dataclass
class BatchConfig:
    """Batch processing configuration."""
    base_batch_size: int = 2
    min_batch_size: int = 1
    max_batch_size: int = 3
    base_delay: float = 3.0
    max_delay: float = 10.0
    success_threshold: float = 0.7
    adaptive_delay: bool = True
    delay_multiplier: float = 1.5
    delay_reduction_factor: float = 0.8

@dataclass
class ConnectionConfig:
    """Connection and network configuration."""
    connection_pool_size: int = 2
    worker_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    max_concurrent_requests: int = 5
    request_timeout: int = 30
    keep_alive: bool = True
    verify_ssl: bool = True
    max_redirects: int = 5

@dataclass
class TimeoutConfig:
    """Timeout configuration."""
    page_load_timeout: int = 30
    element_timeout: int = 10
    dynamic_content_timeout: int = 15
    script_timeout: int = 30
    implicit_wait: int = 5
    navigation_timeout: int = 30
    worker_timeout: int = 60
    retry_delay: int = 5
    max_retries: int = 3

@dataclass
class OutputConfig:
    """Output configuration."""
    directory: str = "output"
    default_file: str = "matches.csv"
    date_format: str = "%Y-%m-%d"
    time_format: str = "%H:%M:%S"
    
    def __post_init__(self):
        """Initialize output directory and ensure it exists."""
        self.directory_path = Path(self.directory)
        self.directory_path.mkdir(parents=True, exist_ok=True)
        self.default_output_path = self.directory_path / self.default_file

@dataclass
class LoggingConfig:
    """Logging configuration."""
    log_level: str = "INFO"
    log_file: str = "output/logs/scraper.log"
    log_directory: str = "output/logs"
    log_format: str = "%(asctime)s,%(msecs)03d %(levelname)s: %(message)s"
    log_date_format: str = "%Y-%m-%d %H:%M:%S"
    log_filename_date_format: str = "%y%m%d"
    log_to_console: bool = False
    log_to_file: bool = True
    max_log_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    quiet_modules: List[str] = field(default_factory=lambda: [
        "urllib3",
        "selenium",
        "src.parser",
        "src.data.h2h_data",
        "src.data.odds_data",
        "src.core.url_verifier"
    ])

@dataclass
class URLConfig:
    """URL and endpoint configuration."""
    base_url: str = "https://www.flashscore.co.ke/basketball/"
    match_url_template: str = "https://www.flashscore.co.ke/match/basketball/{}/#/match-summary/match-summary"
    h2h_url_template: str = "https://www.flashscore.co.ke/match/basketball/{}/#/h2h/overall"
    api_endpoints: Dict[str, str] = field(default_factory=dict)
    allowed_domains: List[str] = field(default_factory=lambda: ["flashscore.co.ke"])

@dataclass
class ScrapingConfig:
    """Scraping behavior configuration."""
    max_matches: int = 3  # Limit for demo/testing
    min_h2h_matches: int = 6  # Minimum H2H matches required
    max_concurrent_requests: int = 5
    max_tabs: int = 1
    success_threshold: float = 0.7

@dataclass
class ChromeOptionsConfig:
    """Chrome browser options configuration."""
    headless: bool = True
    no_sandbox: bool = True
    disable_dev_shm_usage: bool = True
    disable_gpu: bool = True
    window_size: str = "1920,1080"
    disable_extensions: bool = True
    disable_notifications: bool = True
    disable_popup_blocking: bool = True
    disable_infobars: bool = True
    disable_blink_features: str = "AutomationControlled"
    disable_features: str = "IsolateOrigins,site-per-process"
    
    def to_list(self) -> List[str]:
        """Convert configuration to Chrome options list."""
        options = []
        
        if self.headless:
            options.append("--headless=new")
        if self.no_sandbox:
            options.append("--no-sandbox")
        if self.disable_dev_shm_usage:
            options.append("--disable-dev-shm-usage")
        if self.disable_gpu:
            options.append("--disable-gpu")
        if self.window_size:
            options.append(f"--window-size={self.window_size}")
        if self.disable_extensions:
            options.append("--disable-extensions")
        if self.disable_notifications:
            options.append("--disable-notifications")
        if self.disable_popup_blocking:
            options.append("--disable-popup-blocking")
        if self.disable_infobars:
            options.append("--disable-infobars")
        if self.disable_blink_features:
            options.append(f"--disable-blink-features={self.disable_blink_features}")
        if self.disable_features:
            options.append(f"--disable-features={self.disable_features}")
        
        return options

@dataclass
class DataFieldsConfig:
    """Data field definitions for different data types."""
    match_fields: List[str] = field(default_factory=lambda: [
        "country",
        "league", 
        "home_team",
        "away_team",
        "date",
        "time",
        "match_id"
    ])
    
    odds_fields: List[str] = field(default_factory=lambda: [
        "match_id",
        "total_goals",
        "over_odds", 
        "under_odds",
        "last_update"
    ])
    
    h2h_fields: List[str] = field(default_factory=lambda: [
        "match_id",
        "date",
        "home_team",
        "away_team", 
        "home_score",
        "away_score",
        "competition"
    ])
    
    detailed_match_fields: List[str] = field(default_factory=lambda: [
        "match_id",
        "league",
        "home_team", 
        "away_team",
        "status",
        "current_score",
        "quarter_scores",
        "team_stats",
        "player_stats",
        "team_fouls",
        "timeouts",
        "last_update"
    ])

@dataclass
class OutputFilesConfig:
    """Output file configuration."""
    default_output_file: str = "matches.json"
    odds_output_file: str = "match_odds.csv"
    h2h_output_file: str = "h2h_matches.csv"
    log_file_pattern: str = "scraper_{}.log"
    json_file_pattern: str = "matches_{}.json"

@dataclass
class ScraperConfig:
    """Main configuration for the scraper."""
    # Component configurations
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    tab: TabConfig = field(default_factory=TabConfig)
    batch: BatchConfig = field(default_factory=BatchConfig)
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    url: URLConfig = field(default_factory=URLConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    
    # Runtime settings
    debug_mode: bool = False
    save_raw_data: bool = False
    raw_data_dir: str = "raw_data"
    temp_dir: str = "temp"
    
    # Selectors
    selectors: Dict[str, Any] = field(default_factory=dict)
    
    # Scraping behavior configuration
    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
    
    # Chrome browser options configuration
    chrome_options: ChromeOptionsConfig = field(default_factory=ChromeOptionsConfig)
    
    # Data field definitions
    data_fields: DataFieldsConfig = field(default_factory=DataFieldsConfig)
    
    # Output file configuration
    output_files: OutputFilesConfig = field(default_factory=OutputFilesConfig)
    
    def __post_init__(self):
        """Initialize selectors after object creation."""
        # Hardcoded selectors
        self.selectors = {
            'match': {
                'container': 'div.event__match',
                'scheduled': 'div.event__match--scheduled',
                'teams': {
                    'container': 'div.duelParticipant__container',
                    'home': 'div.duelParticipant__home .participant__participantName',
                    'away': 'div.duelParticipant__away .participant__participantName'
                },
                'datetime': {
                    'container': 'div.duelParticipant__startTime'
                },
                'navigation': {
                    'container': 'nav.wcl-breadcrumbs_SRNRR',
                    'items': 'li.wcl-breadcrumbItem_CiWQ7',
                    'text': 'span.wcl-overline_rOFfd',
                    'country': {
                        'index': 1,
                        'name': 'country'
                    },
                    'league': {
                        'index': 2,
                        'name': 'league'
                    }
                }
            },
            'match_info': {
                'navigation': {
                    'container': 'nav.wcl-breadcrumbs_SRNRR',
                    'item': 'li.wcl-breadcrumbItem_CiWQ7',
                    'text': 'span.wcl-overline_rOFfd',
                    'country': {
                        'index': 1,
                        'name': 'country'
                    },
                    'league': {
                        'index': 2,
                        'name': 'league'
                    }
                },
                'teams': {
                    'container': 'div.duelParticipant__container',
                    'home': 'div.duelParticipant__home .participant__participantName',
                    'away': 'div.duelParticipant__away .participant__participantName'
                },
                'datetime': {
                    'container': 'div.duelParticipant__startTime'
                },
                'venue': {
                    'container': 'div.wcl-infoValue_0JeZb',
                    'name': 'strong.wcl-simpleText_Asp-0',
                    'city': 'span.wcl-simpleText_Asp-0'
                }
            },
            'odds': {
                'table': {
                    'container': 'div.oddsTab__tableWrapper',
                    'home_away': {
                        'container': 'div.ui-table.oddsCell__odds',
                        'row': 'div.ui-table__row',
                        'bookmaker': 'div.oddsCell__bookmakerPart',
                        'odds': {
                            'container': 'div.ui-table__body',
                            'value': 'span.wcl-oddsValue_Fc9sZ',
                            'home': {
                                'cell': 'a.oddsCell__odd[data-analytics-element="ODDS_COMPARIONS_ODD_CELL_2"]',
                                'value': 'span'
                            },
                            'away': {
                                'cell': 'a.oddsCell__odd[data-analytics-element="ODDS_COMPARIONS_ODD_CELL_3"]',
                                'value': 'span'
                            }
                        }
                    },
                    'over_under': {
                        'container': 'div.oddsTab__tableWrapper',
                        'row': 'div.ui-table__row',
                        'bookmaker': 'div.oddsCell__bookmakerPart',
                        'odds': {
                            'container': 'div.ui-table__body',
                            'value': 'span.wcl-oddsValue_Fc9sZ',
                            'header': {
                                'container': 'div.ui-table__header',
                                'row': 'div.ui-table__headerCell',
                                'cell': 'div.ui-table__headerCell.oddsCell__header'
                            },
                            'total': {
                                'cell': 'div.wcl-oddsCell_djZ95',
                                'value': 'span.wcl-oddsValue_Fc9sZ'
                            },
                            'over': {
                                'cell': 'a.oddsCell__odd[data-analytics-element="ODDS_COMPARIONS_ODD_CELL_2"]',
                                'value': 'span'
                            },
                            'under': {
                                'cell': 'a.oddsCell__odd[data-analytics-element="ODDS_COMPARIONS_ODD_CELL_3"]',
                                'value': 'span'
                            }
                        }
                    },
                    'removed': 'oddsCell__lineThrough'
                }
            },
            'h2h': {
                'container': 'div.h2h',
                'section': 'div.h2h__section.section',
                'row': 'a.h2h__row',
                'date': 'span.h2h__date',
                'event': {
                    'container': 'span.h2h__event',
                    'name': 'span.h2h__event span'
                },
                'home_participant': 'span.h2h__participant.h2h__homeParticipant .h2h__participantInner',
                'away_participant': 'span.h2h__participant.h2h__awayParticipant .h2h__participantInner',
                'result': {
                    'container': 'span.h2h__result',
                    'home': 'span.h2h__result span:first-child',
                    'away': 'span.h2h__result span:last-child'
                },
                'show_more': 'button.wclButtonLink.wclButtonLink--h2h'
            },
            'match_details': {
                'home_team': '.duelParticipant__home .participant__participantName',
                'away_team': '.duelParticipant__away .participant__participantName',
                'match_time': '.duelParticipant__startTime',
                'tournament_info': '.wcl-breadcrumbList_m5Npe li:nth-child(3)',
                'country': '.wcl-breadcrumbList_m5Npe li:nth-child(2)',
                'league': '.wcl-breadcrumbList_m5Npe li:nth-child(3)',
                'venue': '.wcl-infoValue_0JeZb strong',
                'venue_city': '.wcl-infoValue_0JeZb span'
            },
            'detailed_stats': {
                'quarters': 'div.event__part',
                'score_breakdown': 'div.event__scores',
                'team_stats': 'div.stat__row',
                'player_stats': 'div.stat__row',
                'team_fouls': 'div.stat__row',
                'timeouts': 'div.stat__row'
            },
            'calendar': {
                'navigation': {
                    'tomorrow_button': '[data-day-picker-arrow=\'next\']',
                    'tomorrow_button_alt': '[aria-label=\'Next day\']',
                    'tomorrow_button_class': '.wcl-arrow_8k9lP',
                    'yesterday_button': '[data-day-picker-arrow=\'prev\']',
                    'yesterday_button_alt': '[aria-label=\'Previous day\']',
                    'today_button': '[data-day-picker-arrow=\'today\']',
                    'today_button_alt': '[aria-label=\'Today\']'
                }
            },
            'loading_indicator': 'loader',
            'results': {
                'final_score_wrapper': 'div.detailScore__wrapper',
                'home_score': 'div.detailScore__wrapper > span:first-child',
                'away_score': 'div.detailScore__wrapper > span:last-child',
                'match_status': 'div.detailScore__status > span.fixedHeaderDuel__detailStatus'
            }
        }
        # Merge in any extra selectors from config.json (e.g., 'results')
        if hasattr(self, '_raw_selectors'):
            for k, v in self._raw_selectors.items():
                if k not in self.selectors:
                    self.selectors[k] = v
        elif hasattr(self, 'raw_selectors'):
            for k, v in self.raw_selectors.items():
                if k not in self.selectors:
                    self.selectors[k] = v
        # If loaded from config.json, merge in any extra selectors
        if isinstance(getattr(self, 'selectors', None), dict):
            config_path = 'src/config.json'
            try:
                with open(config_path, 'r') as f:
                    config_dict = json.load(f)
                extra_selectors = config_dict.get('selectors', {})
                for k, v in extra_selectors.items():
                    if k not in self.selectors:
                        self.selectors[k] = v
            except Exception:
                pass
    
    @classmethod
    def load(cls, config_path: str = "src/config.json") -> 'ScraperConfig':
        """Load configuration from a JSON file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            ScraperConfig: Loaded configuration
        """
        try:
            path = Path(config_path)
            if path.exists():
                with open(path, 'r') as f:
                    config_dict = json.load(f)
                logger.info(f"Loaded configuration from {path}")
                
                # Convert nested dictionaries to appropriate config objects
                config_dict = cls._process_config_dict(config_dict)
                return cls(**config_dict)
            else:
                logger.info(f"No config file found at {path}, using defaults")
                return cls()
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            logger.info("Using default configuration")
            return cls()
    
    def save(self, config_path: str = "src/config.json") -> None:
        """Save configuration to a JSON file.
        
        Args:
            config_path: Path to save the configuration file
        """
        try:
            path = Path(config_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert config to dictionary
            config_dict = asdict(self)
            
            # Save to file
            with open(path, 'w') as f:
                json.dump(config_dict, f, indent=4)
            logger.info(f"Saved configuration to {path}")
        except Exception as e:
            logger.error(f"Error saving config to {config_path}: {e}")
    
    def update(self, **kwargs) -> None:
        """Update configuration with new values.
        
        Args:
            **kwargs: Configuration values to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                if isinstance(value, dict) and hasattr(getattr(self, key), '__dataclass_fields__'):
                    # Update nested config object
                    current = getattr(self, key)
                    for k, v in value.items():
                        if hasattr(current, k):
                            setattr(current, k, v)
                else:
                    setattr(self, key, value)
            else:
                logger.warning(f"Unknown config key: {key}")
    
    @staticmethod
    def _process_config_dict(config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Process configuration dictionary to handle nested configs.
        
        Args:
            config_dict: Raw configuration dictionary
            
        Returns:
            Dict[str, Any]: Processed configuration dictionary
        """
        config_classes = {
            'browser': BrowserConfig,
            'tab': TabConfig,
            'batch': BatchConfig,
            'connection': ConnectionConfig,
            'timeout': TimeoutConfig,
            'logging': LoggingConfig,
            'url': URLConfig,
            'output': OutputConfig,
            'scraping': ScrapingConfig,
            'chrome_options': ChromeOptionsConfig,
            'data_fields': DataFieldsConfig,
            'output_files': OutputFilesConfig
        }
        
        processed = {}
        for key, value in config_dict.items():
            if key in config_classes and isinstance(value, dict):
                processed[key] = config_classes[key](**value)
            else:
                processed[key] = value
        return processed

# Create default configuration
DEFAULT_CONFIG = ScraperConfig()

# Load configuration from file if it exists
CONFIG = ScraperConfig.load()

# Export commonly used values for backward compatibility
BASE_URL = CONFIG.url.base_url
WAIT_TIMEOUT = CONFIG.timeout.element_timeout
DYNAMIC_CONTENT_WAIT = CONFIG.timeout.dynamic_content_timeout

# Export new configuration values
MIN_H2H_MATCHES = CONFIG.scraping.min_h2h_matches
MAX_MATCHES = CONFIG.scraping.max_matches
MAX_CONCURRENT_REQUESTS = CONFIG.scraping.max_concurrent_requests
CHROME_OPTIONS = CONFIG.chrome_options.to_list()

# All selectors consolidated into a single dictionary
SELECTORS = {
    'match': {
        'container': 'div.event__match',
        'scheduled': 'div.event__match--scheduled',
        'teams': {
            'container': 'div.duelParticipant__container',
            'home': 'div.duelParticipant__home .participant__participantName',
            'away': 'div.duelParticipant__away .participant__participantName'
        },
        'datetime': {
            'container': 'div.duelParticipant__startTime'
        },
        'navigation': {
            'container': 'nav.wcl-breadcrumbs_SRNRR',
            'items': 'li.wcl-breadcrumbItem_CiWQ7',
            'text': 'span.wcl-overline_rOFfd',
            'country': {
                'index': 1,
                'name': 'country'
            },
            'league': {
                'index': 2,
                'name': 'league'
            }
        }
    },
    'match_info': {
        'navigation': {
            'container': 'nav.wcl-breadcrumbs_SRNRR',
            'item': 'li.wcl-breadcrumbItem_CiWQ7',
            'text': 'span.wcl-overline_rOFfd',
            'country': {
                'index': 1,
                'name': 'country'
            },
            'league': {
                'index': 2,
                'name': 'league'
            }
        },
        'teams': {
            'container': 'div.duelParticipant__container',
            'home': 'div.duelParticipant__home .participant__participantName',
            'away': 'div.duelParticipant__away .participant__participantName'
        },
        'datetime': {
            'container': 'div.duelParticipant__startTime'
        },
        'venue': {
            'container': 'div.wcl-infoValue_0JeZb',
            'name': 'strong.wcl-simpleText_Asp-0',
            'city': 'span.wcl-simpleText_Asp-0'
        }
    },
    'odds': {
        'table': {
            'container': 'div.oddsTab__tableWrapper',
            'home_away': {
                'container': 'div.ui-table.oddsCell__odds',
                'row': 'div.ui-table__row',
                'bookmaker': 'div.oddsCell__bookmakerPart',
                'odds': {
                    'container': 'div.ui-table__body',
                    'value': 'span.wcl-oddsValue_Fc9sZ',
                    'home': {
                        'cell': 'a.oddsCell__odd[data-analytics-element="ODDS_COMPARIONS_ODD_CELL_2"]',
                        'value': 'span'
                    },
                    'away': {
                        'cell': 'a.oddsCell__odd[data-analytics-element="ODDS_COMPARIONS_ODD_CELL_3"]',
                        'value': 'span'
                    }
                }
            },
            'over_under': {
                'container': 'div.oddsTab__tableWrapper',
                'row': 'div.ui-table__row',
                'bookmaker': 'div.oddsCell__bookmakerPart',
                'odds': {
                    'container': 'div.ui-table__body',
                    'value': 'span.wcl-oddsValue_Fc9sZ',
                    'header': {
                        'container': 'div.ui-table__header',
                        'row': 'div.ui-table__headerCell',
                        'cell': 'div.ui-table__headerCell.oddsCell__header'
                    },
                    'total': {
                        'cell': 'div.wcl-oddsCell_djZ95',
                        'value': 'span.wcl-oddsValue_Fc9sZ'
                    },
                    'over': {
                        'cell': 'a.oddsCell__odd[data-analytics-element="ODDS_COMPARIONS_ODD_CELL_2"]',
                        'value': 'span'
                    },
                    'under': {
                        'cell': 'a.oddsCell__odd[data-analytics-element="ODDS_COMPARIONS_ODD_CELL_3"]',
                        'value': 'span'
                    }
                }
            },
            'removed': 'oddsCell__lineThrough'
        }
    },
    'h2h': {
        'container': 'div.h2h',
        'section': 'div.h2h__section.section',
        'row': 'a.h2h__row',
        'date': 'span.h2h__date',
        'event': {
            'container': 'span.h2h__event',
            'name': 'span.h2h__event span'
        },
        'home_participant': 'span.h2h__participant.h2h__homeParticipant .h2h__participantInner',
        'away_participant': 'span.h2h__participant.h2h__awayParticipant .h2h__participantInner',
        'result': {
            'container': 'span.h2h__result',
            'home': 'span.h2h__result span:first-child',
            'away': 'span.h2h__result span:last-child'
        },
        'show_more': 'button.wclButtonLink.wclButtonLink--h2h'
    },
    'match_details': {
        'home_team': '.duelParticipant__home .participant__participantName',
        'away_team': '.duelParticipant__away .participant__participantName',
        'match_time': '.duelParticipant__startTime',
        'tournament_info': '.wcl-breadcrumbList_m5Npe li:nth-child(3)',
        'country': '.wcl-breadcrumbList_m5Npe li:nth-child(2)',
        'league': '.wcl-breadcrumbList_m5Npe li:nth-child(3)',
        'venue': '.wcl-infoValue_0JeZb strong',
        'venue_city': '.wcl-infoValue_0JeZb span'
    },
    'detailed_stats': {
        'quarters': 'div.event__part',
        'score_breakdown': 'div.event__scores',
        'team_stats': 'div.stat__row',
        'player_stats': 'div.stat__row',
        'team_fouls': 'div.stat__row',
        'timeouts': 'div.stat__row'
    },
    'loading_indicator': 'loader'
}

# Required fields for a complete match
REQUIRED_FIELDS = [
    'match_id',      # Unique identifier for the match
    'home_team',     # Home team name
    'away_team',     # Away team name
    'date',          # Match date (YYYY-MM-DD)
    'time',          # Match time (HH:MM:SS)
    'country',       # Country where the match is played
    'league',        # League/tournament name
    'odds',          # Match odds (home/away and over/under)
    'h2h_matches'    # Head-to-head matches
]

# URLs
MATCH_DETAILS_URL = "https://www.flashscore.co.ke/match/basketball/{match_id}/#/match-summary"
H2H_URL = "https://www.flashscore.co.ke/match/basketball/{match_id}/#/h2h/overall"
ODDS_URL_HOME_AWAY = "https://www.flashscore.co.ke/match/basketball/{match_id}/#/odds-comparison/home-away/ft-including-ot"  # For home/away odds
ODDS_URL_OVER_UNDER = "https://www.flashscore.co.ke/match/basketball/{match_id}/#/odds-comparison/over-under/ft-including-ot"  # For over/under odds

# Export data field configurations for backward compatibility
MATCH_FIELDS = CONFIG.data_fields.match_fields
ODDS_FIELDS = CONFIG.data_fields.odds_fields
H2H_FIELDS = CONFIG.data_fields.h2h_fields
DETAILED_MATCH_FIELDS = CONFIG.data_fields.detailed_match_fields

# Export output file configurations for backward compatibility
DEFAULT_OUTPUT_FILE = CONFIG.output_files.default_output_file
ODDS_OUTPUT_FILE = CONFIG.output_files.odds_output_file
H2H_OUTPUT_FILE = CONFIG.output_files.h2h_output_file 