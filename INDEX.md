# Documentation Index

## Quick Navigation

This index helps you find the right documentation for your needs.

---

## 📚 Documentation Overview

| Document | Purpose | Audience |
|----------|---------|----------|
| [README.md](README.md) | Project overview and quick start | Everyone |
| [INDEX.md](INDEX.md) | Documentation navigation guide | Everyone |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | One-page cheat sheet | Everyone |
| [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) | Metrics dashboard usage guide | Everyone |
| [PROJECT_SPEC.md](PROJECT_SPEC.md) | Complete project specification | Project managers, architects |
| [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) | Executive summary and recreation guide | Managers, new team members |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture and design | Architects, developers |
| [DOCUMENTATION.md](DOCUMENTATION.md) | Code documentation and API reference | Developers |
| [OPERATIONS.md](OPERATIONS.md) | Deployment and operations guide | DevOps, operators |
| [GUARANTEES.md](GUARANTEES.md) | Data delivery guarantees explained | Everyone |
| [COMPARISON.md](COMPARISON.md) | Solution comparison matrix | Decision makers |

---

## 🎯 Find What You Need

### I want to...

#### Understand the Project
- **Get a quick overview** → [README.md](README.md)
- **Quick reference card** → [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Executive summary** → [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
- **Understand requirements** → [PROJECT_SPEC.md](PROJECT_SPEC.md) (Business Requirements section)
- **See architecture diagrams** → [ARCHITECTURE.md](ARCHITECTURE.md)
- **Understand data guarantees** → [GUARANTEES.md](GUARANTEES.md)

#### Choose a Solution
- **Compare options** → [COMPARISON.md](COMPARISON.md)
- **Understand costs** → [COMPARISON.md](COMPARISON.md) (Cost section)
- **See architecture differences** → [ARCHITECTURE.md](ARCHITECTURE.md) (Option 1/2/3 sections)

#### Deploy the Solution
- **Deploy ECS Fargate** → [OPERATIONS.md](OPERATIONS.md) (Option 1 Deployment)
- **Deploy AWS Batch** → [OPERATIONS.md](OPERATIONS.md) (Option 2 Deployment)
- **Deploy EC2 Spot** → [OPERATIONS.md](OPERATIONS.md) (Option 3 Deployment)
- **Pre-deployment checklist** → [OPERATIONS.md](OPERATIONS.md) (Pre-Deployment Checklist)

#### Run and Monitor
- **Run a job** → [OPERATIONS.md](OPERATIONS.md) (Running Jobs section)
- **Monitor progress** → [OPERATIONS.md](OPERATIONS.md) (Monitoring section)
- **View metrics dashboard** → [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) 🆕
- **Check logs** → [OPERATIONS.md](OPERATIONS.md) (CloudWatch Logs section)
- **Verify completion** → [OPERATIONS.md](OPERATIONS.md) (Kafka Topic Verification)

#### Troubleshoot Issues
- **Common issues** → [OPERATIONS.md](OPERATIONS.md) (Troubleshooting section)
- **Recovery procedures** → [OPERATIONS.md](OPERATIONS.md) (Recovery Procedures section)
- **Error handling** → [DOCUMENTATION.md](DOCUMENTATION.md) (Error Handling section)

#### Develop and Customize
- **Understand code structure** → [DOCUMENTATION.md](DOCUMENTATION.md)
- **API reference** → [DOCUMENTATION.md](DOCUMENTATION.md) (Core Components section)
- **Modify processor** → [DOCUMENTATION.md](DOCUMENTATION.md) (Code Examples section)
- **Add features** → [PROJECT_SPEC.md](PROJECT_SPEC.md) (Future Enhancements)

#### Maintain the System
- **Regular maintenance** → [OPERATIONS.md](OPERATIONS.md) (Maintenance section)
- **Update dependencies** → [OPERATIONS.md](OPERATIONS.md) (Updating Dependencies)
- **Manage costs** → [OPERATIONS.md](OPERATIONS.md) (Cost Management section)

---

## 📖 Document Details

### README.md
**What it covers:**
- Project overview
- Three solution options
- Key features
- Quick start guide
- Architecture summary
- Performance expectations

**Read this if:** You're new to the project

### PROJECT_SPEC.md
**What it covers:**
- Business requirements
- Technical requirements
- Solution architecture
- Design decisions
- Configuration parameters
- Success criteria
- Risk mitigation

**Read this if:** You need to understand project scope and requirements

### ARCHITECTURE.md
**What it covers:**
- System architecture diagrams
- Component interactions
- Data flow sequences
- Network architecture
- Kafka integration
- Deployment architecture
- Monitoring architecture
- Cost breakdown

**Read this if:** You need to understand how the system works

### DOCUMENTATION.md
**What it covers:**
- CheckpointManager class API
- CSVToKafkaProcessor class API
- Main function flow
- Infrastructure components
- Environment variables
- Dependencies
- Logging
- Error handling
- Performance considerations
- Testing strategies
- Code examples

**Read this if:** You're developing or customizing the code

### OPERATIONS.md
**What it covers:**
- Pre-deployment checklist
- Deployment procedures (all 3 options)
- Running jobs
- Monitoring and logging
- Troubleshooting guide
- Recovery procedures
- Maintenance tasks
- Cost management
- Command reference

**Read this if:** You're deploying or operating the system

### GUARANTEES.md
**What it covers:**
- Kafka producer configuration
- Synchronous confirmation
- Checkpointing mechanism
- Single partition ordering
- Error handling
- Failure scenarios
- Recovery process
- Verification methods
- Trade-offs

**Read this if:** You need to understand data delivery guarantees

### COMPARISON.md
**What it covers:**
- Feature matrix
- Detailed comparison
- Recovery comparison
- Performance comparison
- Cost comparison
- Recommendations

**Read this if:** You're choosing between options

---

## 🗂️ File Structure Reference

```
.
├── README.md                          # Start here
├── INDEX.md                           # This file
├── PROJECT_SPEC.md                    # Project specification
├── ARCHITECTURE.md                    # Architecture documentation
├── DOCUMENTATION.md                   # Code documentation
├── OPERATIONS.md                      # Operations guide
├── GUARANTEES.md                      # Data guarantees
├── COMPARISON.md                      # Solution comparison
├── .gitignore                         # Git ignore rules
│
├── option1-ecs-fargate/
│   ├── README.md                      # ECS-specific guide
│   ├── deploy.sh                      # Deployment script
│   ├── app/
│   │   ├── Dockerfile                 # Container definition
│   │   ├── processor.py               # Main application
│   │   └── requirements.txt           # Python dependencies
│   └── terraform/
│       ├── main.tf                    # Infrastructure code
│       ├── variables.tf               # Configuration variables
│       ├── outputs.tf                 # Resource outputs
│       └── terraform.tfvars.example   # Config template
│
├── option2-aws-batch/
│   ├── README.md                      # Batch-specific guide
│   ├── deploy.sh                      # Deployment script
│   ├── app/
│   │   ├── Dockerfile                 # Container definition
│   │   ├── processor.py               # Main application
│   │   └── requirements.txt           # Python dependencies
│   └── terraform/
│       ├── main.tf                    # Infrastructure code
│       ├── variables.tf               # Configuration variables
│       ├── outputs.tf                 # Resource outputs
│       └── terraform.tfvars.example   # Config template
│
└── option3-ec2-spot/
    ├── README.md                      # EC2-specific guide
    ├── user-data.sh                   # Bootstrap script
    ├── launch-spot.sh                 # Manual launch script
    └── terraform/
        ├── main.tf                    # Infrastructure code
        ├── variables.tf               # Configuration variables
        ├── outputs.tf                 # Resource outputs
        └── terraform.tfvars.example   # Config template
```

---

## 🚀 Quick Start Paths

### Path 1: I want to deploy quickly (EC2 Spot)
1. Read [README.md](README.md) - Overview
2. Read [option3-ec2-spot/README.md](option3-ec2-spot/README.md) - EC2 guide
3. Follow [OPERATIONS.md](OPERATIONS.md) - EC2 deployment section
4. Monitor using [OPERATIONS.md](OPERATIONS.md) - Monitoring section

### Path 2: I want production-ready (ECS Fargate)
1. Read [README.md](README.md) - Overview
2. Read [COMPARISON.md](COMPARISON.md) - Understand why ECS
3. Read [option1-ecs-fargate/README.md](option1-ecs-fargate/README.md) - ECS guide
4. Follow [OPERATIONS.md](OPERATIONS.md) - ECS deployment section
5. Set up monitoring from [OPERATIONS.md](OPERATIONS.md) - Monitoring section

### Path 3: I want cost-optimized (AWS Batch)
1. Read [README.md](README.md) - Overview
2. Read [COMPARISON.md](COMPARISON.md) - Understand cost savings
3. Read [option2-aws-batch/README.md](option2-aws-batch/README.md) - Batch guide
4. Follow [OPERATIONS.md](OPERATIONS.md) - Batch deployment section
5. Monitor costs using [OPERATIONS.md](OPERATIONS.md) - Cost Management section

### Path 4: I need to understand everything first
1. Read [README.md](README.md) - Overview
2. Read [PROJECT_SPEC.md](PROJECT_SPEC.md) - Requirements and design
3. Read [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
4. Read [GUARANTEES.md](GUARANTEES.md) - Data guarantees
5. Read [COMPARISON.md](COMPARISON.md) - Choose option
6. Follow deployment path above

### Path 5: I'm troubleshooting an issue
1. Check [OPERATIONS.md](OPERATIONS.md) - Troubleshooting section
2. Review [OPERATIONS.md](OPERATIONS.md) - Monitoring section
3. Check [DOCUMENTATION.md](DOCUMENTATION.md) - Error Handling section
4. Follow [OPERATIONS.md](OPERATIONS.md) - Recovery Procedures

---

## 🔍 Search by Topic

### AWS Services
- **ECS Fargate** → [ARCHITECTURE.md](ARCHITECTURE.md) (Option 1), [OPERATIONS.md](OPERATIONS.md) (ECS sections)
- **AWS Batch** → [ARCHITECTURE.md](ARCHITECTURE.md) (Option 2), [OPERATIONS.md](OPERATIONS.md) (Batch sections)
- **EC2 Spot** → [ARCHITECTURE.md](ARCHITECTURE.md) (Option 3), [OPERATIONS.md](OPERATIONS.md) (EC2 sections)
- **DynamoDB** → [ARCHITECTURE.md](ARCHITECTURE.md) (Checkpoint), [DOCUMENTATION.md](DOCUMENTATION.md) (CheckpointManager)
- **MSK/Kafka** → [ARCHITECTURE.md](ARCHITECTURE.md) (Kafka Integration), [GUARANTEES.md](GUARANTEES.md)
- **S3** → [ARCHITECTURE.md](ARCHITECTURE.md) (Data Flow), [DOCUMENTATION.md](DOCUMENTATION.md) (S3 Streaming)
- **CloudWatch** → [OPERATIONS.md](OPERATIONS.md) (Monitoring), [ARCHITECTURE.md](ARCHITECTURE.md) (Monitoring Architecture)

### Technical Topics
- **Checkpointing** → [GUARANTEES.md](GUARANTEES.md), [DOCUMENTATION.md](DOCUMENTATION.md) (CheckpointManager)
- **Error Handling** → [GUARANTEES.md](GUARANTEES.md) (Failure Scenarios), [DOCUMENTATION.md](DOCUMENTATION.md) (Error Handling)
- **Sequential Processing** → [GUARANTEES.md](GUARANTEES.md), [PROJECT_SPEC.md](PROJECT_SPEC.md) (Constraints)
- **Recovery** → [OPERATIONS.md](OPERATIONS.md) (Recovery Procedures), [GUARANTEES.md](GUARANTEES.md) (Failure Scenarios)
- **Performance** → [DOCUMENTATION.md](DOCUMENTATION.md) (Performance), [COMPARISON.md](COMPARISON.md) (Performance)
- **Cost** → [COMPARISON.md](COMPARISON.md) (Cost), [OPERATIONS.md](OPERATIONS.md) (Cost Management)
- **Security** → [ARCHITECTURE.md](ARCHITECTURE.md) (Security Groups), [DOCUMENTATION.md](DOCUMENTATION.md) (Security)
- **Testing** → [DOCUMENTATION.md](DOCUMENTATION.md) (Testing), [PROJECT_SPEC.md](PROJECT_SPEC.md) (Testing Strategy)

### Development Topics
- **Python Code** → [DOCUMENTATION.md](DOCUMENTATION.md) (Core Components)
- **Terraform** → [OPERATIONS.md](OPERATIONS.md) (Deployment), [ARCHITECTURE.md](ARCHITECTURE.md) (Infrastructure)
- **Docker** → [OPERATIONS.md](OPERATIONS.md) (Build and Push), option*/app/Dockerfile
- **Environment Variables** → [DOCUMENTATION.md](DOCUMENTATION.md) (Environment Variables)
- **Dependencies** → [DOCUMENTATION.md](DOCUMENTATION.md) (Dependencies), option*/app/requirements.txt

---

## 📝 Document Versions

All documents are version 1.0.0, last updated January 16, 2026.

---

## 🆘 Still Can't Find What You Need?

1. **Check the table of contents** in each document
2. **Use Ctrl+F** to search within documents
3. **Review the file structure** to find specific implementation files
4. **Check CloudWatch logs** for runtime issues
5. **Review AWS documentation** for service-specific details

---

## 📌 Bookmarks

Save these for quick access:

- **Quick Start:** [README.md](README.md)
- **Cheat Sheet:** [QUICK_REFERENCE.md](QUICK_REFERENCE.md) ⭐
- **Dashboard:** [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) 🆕
- **Deployment:** [OPERATIONS.md](OPERATIONS.md) → Pre-Deployment Checklist
- **Troubleshooting:** [OPERATIONS.md](OPERATIONS.md) → Troubleshooting
- **API Reference:** [DOCUMENTATION.md](DOCUMENTATION.md) → Core Components
- **Architecture Diagrams:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Cost Info:** [COMPARISON.md](COMPARISON.md) → Cost Comparison
- **Recreation Guide:** [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) → Quick Recreation Guide

---

**Happy Processing! 🚀**
