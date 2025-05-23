# LDAPie completion for bash
eval "$(_LDAPIE_COMPLETE=bash_source ldapie)"

_ldapie() {
  local cur prev words cword
  _init_completion || return

  # Available commands
  local commands="search info compare schema add delete modify rename interactive history"

  # Global options
  local global_opts="--help --version --install-completion --show-completion --demo"

  # Command-specific options for search
  local search_opts="-u --username -p --password --ssl --port -a --attrs --scope --limit --page-size --json --ldif --csv --tree --output --theme"

  # If we're completing the command name
  if [[ $cword -eq 1 ]]; then
    COMPREPLY=($(compgen -W "$commands $global_opts" -- "$cur"))
    return 0
  fi

  # Handle subcommand argument and option completion
  local command="${words[1]}"
  case "$command" in
    search)
      if [[ $cword -eq 2 ]]; then
        _known_hosts_real "$cur"
      elif [[ $cword -ge 3 ]]; then
        COMPREPLY=($(compgen -W "$search_opts" -- "$cur"))
      fi
      ;;
    info|compare|schema|add|delete|modify|rename|interactive)
      if [[ $cword -eq 2 ]]; then
        _known_hosts_real "$cur"
      fi
      ;;
  esac

  return 0
}

complete -F _ldapie ldapie
