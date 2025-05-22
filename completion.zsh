# LDAPie completion for zsh
eval "$(_LDAPIE_COMPLETE=zsh_source ldapie)"  # Make sure this uses ldapie, not ldapcli

_ldapie() {
  local -a commands
  local -a opts
  
  commands=(
    'search:Search the LDAP directory'
    'info:Show information about LDAP server'
    'compare:Compare two LDAP entries'
    'schema:Get schema information from LDAP server'
    'add:Add a new entry to the LDAP directory'
    'delete:Delete an entry from the LDAP directory'
    'modify:Modify an existing LDAP entry'
    'rename:Rename or move an LDAP entry'
    'interactive:Start interactive LDAP console'
  )

  # Global options
  opts=(
    '--help:Show help information'
    '--version:Show version information'
  )

  # Command-specific options for search
  local -a search_opts
  search_opts=(
    '-u:Bind DN for authentication'
    '--username:Bind DN for authentication'
    '-p:Password for authentication'
    '--password:Password for authentication'
    '--ssl:Use SSL/TLS connection'
    '--port:LDAP port (default: 389, or 636 with SSL)'
    '-a:Attributes to fetch (can be used multiple times)'
    '--attrs:Attributes to fetch (can be used multiple times)'
    '--scope:Search scope (base, one, sub)'
    '--limit:Maximum number of entries to return'
    '--page-size:Page size for paged results'
    '--json:Output in JSON format'
    '--ldif:Output in LDIF format'
    '--csv:Output in CSV format'
    '--tree:Display results as a tree'
    '--output:Save results to a file'
    '--theme:Color theme (dark, light)'
  )

  # Handle command completion
  if (( CURRENT == 2 )); then
    _describe -t commands 'ldapie commands' commands
    _describe -t options 'ldapie options' opts
    return
  fi

  # Handle subcommand argument and option completion
  local command="${words[2]}"
  case "${command}" in
    search)
      if (( CURRENT == 3 )); then
        _hosts
      elif (( CURRENT >= 4 )); then
        _describe -t options 'search options' search_opts
      fi
      ;;
    info)
      if (( CURRENT == 3 )); then
        _hosts
      fi
      ;;
    compare)
      if (( CURRENT == 3 )); then
        _hosts
      fi
      ;;
    schema)
      if (( CURRENT == 3 )); then
        _hosts
      fi
      ;;
    add)
      if (( CURRENT == 3 )); then
        _hosts
      fi
      ;;
    delete)
      if (( CURRENT == 3 )); then
        _hosts
      fi
      ;;
    modify)
      if (( CURRENT == 3 )); then
        _hosts
      fi
      ;;
    rename)
      if (( CURRENT == 3 )); then
        _hosts
      fi
      ;;
    interactive)
      if (( CURRENT == 3 )); then
        _hosts
      fi
      ;;
  esac
}

compdef _ldapie ldapie
