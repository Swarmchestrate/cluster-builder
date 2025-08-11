# PostgreSQL Database Setup (One-Time Process)

This guide explains how to set up a PostgreSQL database for Swarmchestrate.
Note: This is a one-time setup process. 

---

## 1. Install PostgreSQL

Follow the official PostgreSQL installation guide based on your OS:  
🔗 [PostgreSQL Downloads](https://www.postgresql.org/download/)

###  Example for AWS EC2 (Amazon Linux 2 / Amazon Linux 2023)

```bash
# Install PostgreSQL 15
sudo yum install postgresql15 postgresql15-server -y

# Initialize PostgreSQL database
sudo su - postgres -c "/usr/bin/initdb -D /var/lib/pgsql/15/data/"

# Enable and start PostgreSQL service
sudo systemctl enable postgresql-15
sudo systemctl start postgresql-15
```

---

## 2. Configure PostgreSQL User and Database

### Switch to PostgreSQL User:

```bash
sudo -i -u postgres
```

### Access PostgreSQL Shell:

```bash
psql
```

###  Run the following SQL commands:

```sql
CREATE DATABASE your_database;
CREATE USER your_user WITH ENCRYPTED PASSWORD 'your_password';
ALTER ROLE your_user SUPERUSER;
GRANT ALL PRIVILEGES ON DATABASE your_database TO your_user;
```

###  Exit PostgreSQL shell:

```bash
\q
```

### Exit PostgreSQL user:

```bash
exit
```

---

## 3. Allow Remote Connections

### Edit PostgreSQL configuration:

```bash
sudo nano /var/lib/pgsql/15/data/postgresql.conf
```

**Find and modify:**

```ini
listen_addresses = 'localhost'
```

➡️ Change to:

```ini
listen_addresses = '*'
```

**Save and exit.**

---

###  Edit pg_hba.conf:

```bash
sudo nano /var/lib/pgsql/15/data/pg_hba.conf
```

**Add at the end:**

```ini
# Allow all connections with md5 password
host    all             all             0.0.0.0/0               md5
host    all             all             ::/0                    md5
```

**Save and exit.**

---

###  Restart PostgreSQL to apply changes:

```bash
sudo systemctl restart postgresql-15
```

---

## 4. Connect to PostgreSQL Remotely (Test Connection)

```bash
psql -h <postgres-server-ip> -U your_user -d your_database
```

---

### Notes:
- This setup is a **one-time process**.
- Replace `<postgres-server-ip>` with the actual IP of your PostgreSQL instance.
- Adjust PostgreSQL version `15` in paths if using a different version.

---
