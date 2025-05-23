# LDAPie completion for fish
# To use this file, copy it to ~/.config/fish/completions/ldapie.fish

# Use Click's built-in fish completion
eval (env _LDAPIE_COMPLETE=fish_source ldapie)

# Additional custom completions 
function __fish_ldapie_no_subcommand
  set cmd (commandline -opc)
  if [ (count $cmd) -eq 1 ]
    return 0
  end
  return 1
end

function __fish_ldapie_using_command
  set cmd (commandline -opc)
  if [ (count $cmd) -gt 1 ]
    if [ $argv[1] = $cmd[2] ]
      return 0
    end
  end
  return 1
end

# Main commands
complete -f -c ldapie -n '__fish_ldapie_no_subcommand' -a search -d 'Search the LDAP directory'
complete -f -c ldapie -n '__fish_ldapie_no_subcommand' -a info -d 'Show information about LDAP server'
complete -f -c ldapie -n '__fish_ldapie_no_subcommand' -a compare -d 'Compare two LDAP entries'
complete -f -c ldapie -n '__fish_ldapie_no_subcommand' -a schema -d 'Get schema information from LDAP server'
complete -f -c ldapie -n '__fish_ldapie_no_subcommand' -a add -d 'Add a new entry to the LDAP directory'
complete -f -c ldapie -n '__fish_ldapie_no_subcommand' -a delete -d 'Delete an entry from the LDAP directory'
complete -f -c ldapie -n '__fish_ldapie_no_subcommand' -a modify -d 'Modify an existing LDAP entry'
complete -f -c ldapie -n '__fish_ldapie_no_subcommand' -a rename -d 'Rename or move an LDAP entry'
complete -f -c ldapie -n '__fish_ldapie_no_subcommand' -a interactive -d 'Start interactive LDAP console'

# Global options
complete -f -c ldapie -n '__fish_ldapie_no_subcommand' -l help -d 'Show help information'
complete -f -c ldapie -n '__fish_ldapie_no_subcommand' -l version -d 'Show version information'
complete -f -c ldapie -n '__fish_ldapie_no_subcommand' -l install-completion -d 'Install completion for the current shell'
complete -f -c ldapie -n '__fish_ldapie_no_subcommand' -l show-completion -d 'Show completion for the current shell'
complete -f -c ldapie -n '__fish_ldapie_no_subcommand' -l demo -d 'Run the automated demo'

# Search options
complete -f -c ldapie -n '__fish_ldapie_using_command search' -s u -l username -d 'Bind DN for authentication'
complete -f -c ldapie -n '__fish_ldapie_using_command search' -s p -l password -d 'Password for authentication'
complete -f -c ldapie -n '__fish_ldapie_using_command search' -l ssl -d 'Use SSL/TLS connection'
complete -f -c ldapie -n '__fish_ldapie_using_command search' -l port -d 'LDAP port (default: 389, or 636 with SSL)'
complete -f -c ldapie -n '__fish_ldapie_using_command search' -s a -l attrs -d 'Attributes to fetch (can be used multiple times)'
complete -f -c ldapie -n '__fish_ldapie_using_command search' -l scope -d 'Search scope (base, one, sub)'
complete -f -c ldapie -n '__fish_ldapie_using_command search' -l limit -d 'Maximum number of entries to return'
complete -f -c ldapie -n '__fish_ldapie_using_command search' -l page-size -d 'Page size for paged results'
complete -f -c ldapie -n '__fish_ldapie_using_command search' -l json -d 'Output in JSON format'
complete -f -c ldapie -n '__fish_ldapie_using_command search' -l ldif -d 'Output in LDIF format'
complete -f -c ldapie -n '__fish_ldapie_using_command search' -l csv -d 'Output in CSV format'
complete -f -c ldapie -n '__fish_ldapie_using_command search' -l tree -d 'Display results as a tree'
complete -f -c ldapie -n '__fish_ldapie_using_command search' -l output -d 'Save results to a file'
complete -f -c ldapie -n '__fish_ldapie_using_command search' -l theme -d 'Color theme (dark, light)'

# Known hosts completion for the first argument of each command
complete -f -c ldapie -n '__fish_ldapie_using_command search; and not __fish_seen_argument -s h' -a "(cat ~/.ssh/known_hosts | cut -d ' ' -f 1 | cut -d ',' -f 1)"
complete -f -c ldapie -n '__fish_ldapie_using_command info; and not __fish_seen_argument -s h' -a "(cat ~/.ssh/known_hosts | cut -d ' ' -f 1 | cut -d ',' -f 1)"
complete -f -c ldapie -n '__fish_ldapie_using_command compare; and not __fish_seen_argument -s h' -a "(cat ~/.ssh/known_hosts | cut -d ' ' -f 1 | cut -d ',' -f 1)"
complete -f -c ldapie -n '__fish_ldapie_using_command schema; and not __fish_seen_argument -s h' -a "(cat ~/.ssh/known_hosts | cut -d ' ' -f 1 | cut -d ',' -f 1)"
complete -f -c ldapie -n '__fish_ldapie_using_command add; and not __fish_seen_argument -s h' -a "(cat ~/.ssh/known_hosts | cut -d ' ' -f 1 | cut -d ',' -f 1)"
complete -f -c ldapie -n '__fish_ldapie_using_command delete; and not __fish_seen_argument -s h' -a "(cat ~/.ssh/known_hosts | cut -d ' ' -f 1 | cut -d ',' -f 1)"
complete -f -c ldapie -n '__fish_ldapie_using_command modify; and not __fish_seen_argument -s h' -a "(cat ~/.ssh/known_hosts | cut -d ' ' -f 1 | cut -d ',' -f 1)"
complete -f -c ldapie -n '__fish_ldapie_using_command rename; and not __fish_seen_argument -s h' -a "(cat ~/.ssh/known_hosts | cut -d ' ' -f 1 | cut -d ',' -f 1)"
complete -f -c ldapie -n '__fish_ldapie_using_command interactive; and not __fish_seen_argument -s h' -a "(cat ~/.ssh/known_hosts | cut -d ' ' -f 1 | cut -d ',' -f 1)"
